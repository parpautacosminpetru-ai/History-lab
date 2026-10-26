"""Local Windows-capable Tk workbench; AI is invoked only through the CLI."""
from __future__ import annotations

from functools import wraps
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,simpledialog,messagebox

from PIL import Image,ImageTk

from .coverage import coverage
from .ingestion import import_pdf,correct_structure
from .packages import export_package
from .semantics import create_node,annotate,relation,review,publish,provenance
from .db import normalize,transaction


def guarded(function):
    @wraps(function)
    def call(*args,**kwargs):
        try:
            return function(*args,**kwargs)
        except Exception as error:
            messagebox.showerror('HUI',str(error))
    return call


class Workbench:
    def __init__(self,root,db,workspace):
        self.root,self.db,self.workspace = root,db,Path(workspace)
        self.segment,self.image,self.photo = None,None,None
        root.title('HUI — Atelier local de indexare și validare')
        root.geometry('1320x900')
        toolbar = ttk.Frame(root,padding=8);toolbar.pack(fill='x')
        for label,command in [('Import PDF',self.import_document),('Publică + exportă',self.export),
                              ('Acoperire',self.metrics),('Structură',self.structure),('Pagină tipărită',self.printed_page),
                              ('Transcriere verificată',self.verify_transcription)]:
            ttk.Button(toolbar,text=label,command=guarded(command)).pack(side='left',padx=3)
        self.pages = ttk.Combobox(root,state='readonly',width=100)
        self.pages.pack(fill='x',padx=8)
        self.pages.bind('<<ComboboxSelected>>',lambda _:self.show_page())
        panes = ttk.Panedwindow(root,orient='horizontal');panes.pack(fill='both',expand=True,padx=8,pady=8)
        self.canvas = tk.Canvas(panes,background='#dfe4e4',width=600)
        right = ttk.Frame(panes)
        panes.add(self.canvas,weight=1);panes.add(right,weight=1)
        ttk.Label(right,text='Text extras nemodificat • selectează intervalul exact').pack(anchor='w')
        self.text = tk.Text(right,wrap='word',font=('Segoe UI',11),height=14,exportselection=False)
        self.text.pack(fill='both',expand=True)
        self.text.bind('<Key>',lambda e: None if (e.state & 4 and e.keysym.lower() in ('c','a')) else 'break')
        self.text.bind('<ButtonRelease-1>',lambda _:self.highlight())
        nodebar = ttk.Frame(right);nodebar.pack(fill='x',pady=5)
        self.nodes = ttk.Combobox(nodebar,state='readonly',width=38)
        self.nodes.pack(side='left',fill='x',expand=True)
        ttk.Button(nodebar,text='Indice nou',command=guarded(self.new_node)).pack(side='left')
        ttk.Button(nodebar,text='Adnotează selecția',command=guarded(self.annotate)).pack(side='left')
        relationbar = ttk.Frame(right);relationbar.pack(fill='x')
        self.subject,self.obj = ttk.Combobox(relationbar,state='readonly'),ttk.Combobox(relationbar,state='readonly')
        self.subject.pack(side='left',fill='x',expand=True);self.obj.pack(side='left',fill='x',expand=True)
        ttk.Button(relationbar,text='Relație în selecție',command=guarded(self.add_relation)).pack(side='left')
        ttk.Label(right,text='Propuneri • selectare multiplă pentru revizuire în lot').pack(anchor='w',pady=5)
        self.pending = tk.Listbox(right,selectmode='extended',height=9,exportselection=False)
        self.pending.pack(fill='both',expand=True)
        self.pending.bind('<<ListboxSelect>>',lambda _:self.inspect())
        self.detail = tk.Text(right,height=5,wrap='word');self.detail.pack(fill='x')
        decisions = ttk.Frame(right);decisions.pack(fill='x')
        for label,status in [('Confirmă','human_confirmed'),('Respinge','rejected'),('Reverifică','needs_review')]:
            ttk.Button(decisions,text=label,command=guarded(lambda s=status:self.decide(s))).pack(side='left')
        ttk.Button(decisions,text='Corectează eticheta',command=guarded(self.correct_node)).pack(side='left')
        self.canvas.bind('<Configure>',lambda _:self.render())
        self.refresh()

    def refresh(self):
        self.page_rows = self.db.execute('SELECT p.*,s.title FROM Pages p JOIN SourceEditions e ON e.id=p.edition_id JOIN Sources s ON s.id=e.source_id ORDER BY s.title,p.pdf_page').fetchall()
        self.pages['values'] = [f'{r["title"]} / PDF {r["pdf_page"]} / {r["edition_id"][:8]}' for r in self.page_rows]
        self.node_rows = self.db.execute("SELECT * FROM IndexNodes WHERE verification!='rejected' ORDER BY canonical_label,id").fetchall()
        self.nodes['values'] = [f'{r["canonical_label"]} [{r["node_type"]}] — {r["disambiguation"]} ({r["id"][:8]})' for r in self.node_rows]
        self.pending_rows = []
        for kind,table,label in [('node','IndexNodes','canonical_label'),('occurrence','Occurrences','original_form'),('relation','ExplicitRelations','predicate')]:
            self.pending_rows.extend((kind,dict(r)) for r in self.db.execute(f"SELECT *,{label} AS label FROM {table} WHERE verification IN ('proposed','auto_validated','needs_review') ORDER BY id LIMIT 500"))
        self.pending.delete(0,'end')
        for kind,row in self.pending_rows:
            self.pending.insert('end',f'{kind} / {row["verification"]} / {row["label"][:95]}')
        if self.pages.current()<0 and self.page_rows:
            self.pages.current(0)
        self.show_page()

    @guarded
    def show_page(self):
        if self.pages.current()<0:return
        page = self.page_rows[self.pages.current()]
        self.segment = self.db.execute('SELECT * FROM TextSegments WHERE page_id=?',(page['id'],)).fetchone()
        self.text.delete('1.0','end');self.text.insert('1.0',page['raw_text'])
        path = self.workspace/page['image_path']
        self.image = Image.open(path).copy() if path.exists() else None
        self.render()
        self.occurrence_rows = self.db.execute("SELECT o.*,n.canonical_label FROM Occurrences o JOIN IndexNodes n ON n.id=o.node_id JOIN SpanParts sp ON sp.span_id=o.span_id WHERE sp.segment_id=? AND o.verification!='rejected' ORDER BY sp.start_offset,o.id",(self.segment['id'] if self.segment else '',)).fetchall()
        values = [f'{r["canonical_label"]} ({r["id"][:8]})' for r in self.occurrence_rows]
        self.subject['values']=values;self.obj['values']=values

    def render(self):
        self.canvas.delete('all')
        if self.image:
            image = self.image.copy()
            image.thumbnail((max(10,self.canvas.winfo_width()),max(10,self.canvas.winfo_height())))
            self.photo=ImageTk.PhotoImage(image)
            self.canvas.create_image(0,0,image=self.photo,anchor='nw')
            self.draw_size=image.size

    def selection(self):
        if not self.segment or not self.text.tag_ranges('sel'):
            raise ValueError('Selectează un interval din textul original')
        start=len(self.text.get('1.0','sel.first'))
        end=start+len(self.text.get('sel.first','sel.last'))
        return {'segment_id':self.segment['id'],'start':start,'end':end}

    def highlight(self):
        self.render()
        try: selection=self.selection()
        except ValueError:return
        if not self.image:return
        w,h=self.draw_size
        for box in self.db.execute('SELECT * FROM TextBoxes WHERE segment_id=? AND start_offset<? AND end_offset>?',(self.segment['id'],selection['end'],selection['start'])):
            self.canvas.create_rectangle(box['x0']*w,box['y0']*h,box['x1']*w,box['y1']*h,outline='#bd7500',fill='#ffe187',stipple='gray50')

    def import_document(self):
        paths=filedialog.askopenfilenames(filetypes=[('Documente PDF','*.pdf')])
        if not paths:return
        language=simpledialog.askstring('Limbă','Codul limbii (ro, en, fr, de, la sau und):',initialvalue='ro')
        if language is None:return
        ocr=simpledialog.askstring('OCR local','Limba Tesseract pentru scanări (ron/eng/fra/deu/lat); gol = fără OCR:',initialvalue='')
        for path in paths:
            title=simpledialog.askstring('Sursă','Titlul exact:',initialvalue=Path(path).stem)
            if title:
                author=simpledialog.askstring('Autor','Autorul, dacă este cunoscut:',initialvalue='')
                import_pdf(self.db,self.workspace,Path(path),title=title,authors=[author] if author else [],language=language or 'und',ocr_language=ocr or None)
        self.refresh()

    def new_node(self):
        label=simpledialog.askstring('Indice nou','Etichetă canonică:')
        if not label:return
        kind=simpledialog.askstring('Tip','Tip explicit (person, institution, concept, locality etc.):',initialvalue='concept')
        if not kind:return
        disambiguation=simpledialog.askstring('Dezambiguizare','Precizare pentru omonime (nu se comasează automat):',initialvalue='')
        create_node(self.db,label,kind,disambiguation=disambiguation or '')
        self.refresh()

    def annotate(self):
        selection=self.selection()
        if self.nodes.current()<0:raise ValueError('Alege identitatea indicelui')
        annotate(self.db,self.node_rows[self.nodes.current()]['id'],[selection])
        self.refresh()

    def add_relation(self):
        selection=self.selection()
        if self.subject.current()<0 or self.obj.current()<0:raise ValueError('Alege cele două apariții din pasaj')
        predicate=simpledialog.askstring('Relație','Tipul relației explicite:',initialvalue='causality')
        connector=simpledialog.askstring('Conector','Copiază conectorul exact din text:')
        modality=simpledialog.askstring('Modalitate','Modalitate conservată (assertive/conditional/possible/etc.):',initialvalue='assertive')
        attribution=simpledialog.askstring('Atribuire','Vocea / autorul exact (gol numai dacă nu există atribuire):',initialvalue='')
        if not predicate or not connector or not modality or attribution is None:return
        negated=messagebox.askyesno('Negație','Pasajul neagă relația?')
        relation(self.db,self.occurrence_rows[self.subject.current()]['id'],predicate,self.occurrence_rows[self.obj.current()]['id'],
                 [selection],connector=connector,negated=negated,modality=modality,attribution=attribution)
        self.refresh()

    @guarded
    def inspect(self):
        selected=self.pending.curselection()
        if not selected:return
        kind,row=self.pending_rows[selected[0]]
        self.detail.delete('1.0','end')
        self.detail.insert('1.0','\n'.join(f'{k}: {v}' for k,v in row.items()))
        occurrence_id=row['id'] if kind=='occurrence' else None
        if kind=='relation':
            link=self.db.execute('SELECT subject_occurrence_id FROM RelationEvidence WHERE relation_id=? LIMIT 1',(row['id'],)).fetchone()
            occurrence_id=link[0] if link else None
        if occurrence_id:
            trace=provenance(self.db,occurrence_id);p=trace['parts'][0]
            page=self.db.execute('SELECT page_id FROM TextSegments WHERE id=?',(p['segment_id'],)).fetchone()[0]
            for i,item in enumerate(self.page_rows):
                if item['id']==page:self.pages.current(i);self.show_page();break
            start,end=p['start_offset'],p['end_offset']
            self.text.tag_add('sel',f'1.0+{start}c',f'1.0+{end}c');self.highlight()

    def decide(self,status):
        selected=self.pending.curselection()
        if not selected:return
        reviewer=simpledialog.askstring('Revizuire umană','Numele revizorului:')
        if not reviewer:return
        decisions=[{'type':self.pending_rows[i][0],'id':self.pending_rows[i][1]['id'],'status':status} for i in selected]
        review(self.db,decisions,reviewer=reviewer)
        self.refresh()

    def correct_node(self):
        selected=self.pending.curselection()
        if len(selected)!=1 or self.pending_rows[selected[0]][0]!='node':raise ValueError('Selectează un indice propus')
        row=self.pending_rows[selected[0]][1]
        label=simpledialog.askstring('Corectare','Etichetă:',initialvalue=row['canonical_label'])
        reviewer=simpledialog.askstring('Corectare','Numele revizorului:') if label else None
        if not reviewer:return
        with transaction(self.db):
            self.db.execute("UPDATE IndexNodes SET canonical_label=?,normalized_label=? WHERE id=? AND verification!='human_confirmed'",(label,normalize(label),row['id']))
            review(self.db,[{'type':'node','id':row['id'],'status':'needs_review'}],reviewer=reviewer,note=f'Etichetă veche: {row["canonical_label"]}; etichetă nouă: {label}')
        self.refresh()

    def structure(self):
        if not self.segment:return
        structure=self.db.execute('SELECT * FROM DocumentStructures WHERE id=?',(self.segment['structure_id'],)).fetchone()
        title=simpledialog.askstring('Structură','Titlul structurii:',initialvalue=structure['title'])
        start=simpledialog.askinteger('Structură','Prima pagină PDF:',initialvalue=structure['start_page']) if title else None
        end=simpledialog.askinteger('Structură','Ultima pagină PDF:',initialvalue=structure['end_page']) if start else None
        reviewer=simpledialog.askstring('Structură','Revizor:') if end else None
        if reviewer:correct_structure(self.db,structure['id'],title=title,start_page=start,end_page=end,reviewer=reviewer);self.refresh()

    def printed_page(self):
        if self.pages.current()<0:return
        page=self.page_rows[self.pages.current()]
        label=simpledialog.askstring('Pagina tipărită','Eticheta exactă (inclusiv numere romane):',initialvalue=page['printed_page'] or '')
        if label is not None:
            with transaction(self.db):self.db.execute('UPDATE Pages SET printed_page=? WHERE id=?',(label or None,page['id']))
            self.refresh()

    def verify_transcription(self):
        if self.pages.current()<0:return
        if messagebox.askyesno('Confruntare','Ai confruntat integral textul extras cu imaginea paginii? Aceasta nu confirmă exhaustivitatea semantică.'):
            with transaction(self.db):self.db.execute('UPDATE Pages SET transcription_verified=1 WHERE id=?',(self.page_rows[self.pages.current()]['id'],))
            self.refresh()

    def export(self):
        output=filedialog.asksaveasfilename(defaultextension='.hui',filetypes=[('Index HUI','*.hui')])
        if not output:return
        include=messagebox.askyesno('Documente originale','Incluzi PDF-urile și imaginile? Continuând confirmi dreptul de distribuire a acestor fișiere.')
        publish(self.db,'Publicare prin atelier')
        export_package(self.db,self.workspace,Path(output),include_originals=include,rights_confirmed=include)
        messagebox.showinfo('HUI','Pachetul a fost exportat.')

    def metrics(self):
        metrics=coverage(self.db)
        messagebox.showinfo('Acoperire măsurată','\n'.join(f'{k}: {len(v) if isinstance(v,list) else v}' for k,v in metrics.items()))


def run(db,workspace):
    root=tk.Tk();Workbench(root,db,workspace);root.mainloop()
