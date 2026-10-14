import ro.historylab.TimelineOrder;

public class TimelineOrderTest {
    public static void main(String[] args) {
        assertYear("1848",1848);
        assertYear(" 1918-1920",1918);
        assertYear("circa 1848",-1);
        assertYear("sec. XVII",-1);
        assertYear("184",-1);
        assertYear("",-1);
        assertYear(null,-1);
        System.out.println("TimelineOrderTest OK");
    }
    static void assertYear(String s,int expected) {
        int got=TimelineOrder.leadingYear(s);
        if(got!=expected)throw new AssertionError("Expected "+expected+" for '"+s+"', got "+got);
    }
}
