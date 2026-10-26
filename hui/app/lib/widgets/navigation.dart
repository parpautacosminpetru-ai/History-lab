import 'package:flutter/material.dart';

class Crumb {
  const Crumb(this.label,this.route);
  final String label,route;
}

void pushResearch(BuildContext context, List<Crumb> trail, String label,
    Widget Function(List<Crumb>) builder) {
  final name='/research/${DateTime.now().microsecondsSinceEpoch}';
  final next=[...trail,Crumb(label,name)];
  Navigator.of(context).push(MaterialPageRoute<void>(
    settings:RouteSettings(name:name),builder:(_)=>builder(next)));
}

class TrailBar extends StatelessWidget {
  const TrailBar({super.key,required this.trail});
  final List<Crumb> trail;
  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    scrollDirection:Axis.horizontal,
    child:Row(children:[for(final item in trail) TextButton(
      onPressed:()=>Navigator.of(context).popUntil((route)=>route.settings.name==item.route || route.isFirst),
      child:Text(item.label))]));
}

String verificationLabel(Object? value) => const {
  'proposed':'Propus', 'auto_validated':'Coordonate verificate automat',
  'needs_review':'Necesită verificare', 'human_confirmed':'Confirmat uman', 'rejected':'Respins'
}[value] ?? 'Fără adnotare semantică';
