package ro.historylab;

/** Referință mecanică din câmpurile completate de istoric, fără date inventate. */
public final class CitationFormatter {
    private CitationFormatter() { }

    public static String format(String author, String title, String date, String archiveRef) {
        StringBuilder out = new StringBuilder();
        append(out, author);
        if (has(title)) {
            if (out.length() > 0) out.append(", ");
            out.append('„').append(title.trim()).append('”');
        }
        if (has(date)) {
            if (out.length() > 0) out.append(", ");
            out.append(date.trim());
        }
        if (has(archiveRef)) {
            if (out.length() > 0) out.append(", ");
            out.append(archiveRef.trim());
        }
        if (out.length() > 0) out.append('.');
        return out.toString();
    }

    private static void append(StringBuilder out, String value) {
        if (has(value)) out.append(value.trim());
    }

    private static boolean has(String value) {
        return value != null && !value.trim().isEmpty();
    }
}
