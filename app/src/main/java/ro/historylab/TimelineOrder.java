package ro.historylab;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Ordine mecanică după primul an de patru cifre introdus explicit de istoric. */
public final class TimelineOrder {
    private static final Pattern FIRST_YEAR = Pattern.compile("^\\s*([0-9]{4})(?=$|[^0-9])");
    private TimelineOrder() {}

    /** -1 când data lipsește sau nu începe cu un an de patru cifre. */
    public static int leadingYear(String enteredDate) {
        if (enteredDate == null) return -1;
        Matcher matcher = FIRST_YEAR.matcher(enteredDate);
        return matcher.find() ? Integer.parseInt(matcher.group(1)) : -1;
    }
}
