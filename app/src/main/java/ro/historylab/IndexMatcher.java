package ro.historylab;

import java.text.Normalizer;
import java.util.Locale;

/** Indexare literală, transparentă. Nu extrage entități și nu deduce contexte. */
public final class IndexMatcher {
    private IndexMatcher() { }

    public static String normalize(String value) {
        if (value == null) return "";
        return Normalizer.normalize(value, Normalizer.Form.NFC).toLowerCase(Locale.ROOT);
    }

    /** Caută expresii exacte, fără a confunda «Bacău» cu «Bacăului». */
    public static boolean containsTerm(String text, String needle) {
        String s = normalize(text);
        String n = normalize(needle == null ? "" : needle.trim());
        if (n.isEmpty()) return false;
        int from = 0;
        while (from <= s.length() - n.length()) {
            int i = s.indexOf(n, from);
            if (i < 0) return false;
            int end = i + n.length();
            boolean startBoundary = i == 0 || !Character.isLetterOrDigit(s.codePointBefore(i));
            boolean endBoundary = end == s.length() || !Character.isLetterOrDigit(s.codePointAt(end));
            if (startBoundary && endBoundary) return true;
            from = i + 1;
        }
        return false;
    }
}
