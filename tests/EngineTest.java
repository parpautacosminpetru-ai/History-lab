import ro.historylab.CitationFormatter;
import ro.historylab.IndexMatcher;
public class EngineTest {
    public static void main(String[] args) {
        check(IndexMatcher.containsTerm("Din orașul Bacău, 1900", "Bacău"));
        check(IndexMatcher.containsTerm("BACĂU; Bacău.", "bAcĂu"));
        check(!IndexMatcher.containsTerm("din Bacăului", "Bacău"));
        check(!IndexMatcher.containsTerm("Iași", "Bacău"));
        check(!IndexMatcher.containsTerm("", ""));
        check(CitationFormatter.format("I. Popescu", "Raport", "1901", "ANIC, fond X")
             .equals("I. Popescu, „Raport”, 1901, ANIC, fond X."));
        check(CitationFormatter.format("", "Act", "", "").equals("„Act”."));
        System.out.println("Teste de indexare și citare: OK");
    }
    private static void check(boolean ok) { if(!ok)throw new AssertionError("Test eșuat"); }
}
