package todo;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.stream.Collectors;

public class Task {
    public enum Priority { LOW, MED, HIGH }

    private final int id;
    private String title;
    private LocalDate due;              // nullable
    private Priority priority;          // default MED
    private boolean done;
    private Set<String> tags;           // comma-separated in file
    private LocalDate created;
    private LocalDate updated;
    private String notes;               // optional

    private static final DateTimeFormatter ISO = DateTimeFormatter.ISO_LOCAL_DATE;

    public Task(int id, String title) {
        this.id = id;
        this.title = title;
        this.priority = Priority.MED;
        this.done = false;
        this.tags = new LinkedHashSet<>();
        this.created = LocalDate.now();
        this.updated = LocalDate.now();
        this.notes = "";
    }

    // Getters/setters
    public int getId() { return id; }
    public String getTitle() { return title; }
    public void setTitle(String t) { this.title = t; touch(); }
    public LocalDate getDue() { return due; }
    public void setDue(LocalDate d) { this.due = d; touch(); }
    public Priority getPriority() { return priority; }
    public void setPriority(Priority p) { this.priority = p; touch(); }
    public boolean isDone() { return done; }
    public void setDone(boolean d) { this.done = d; touch(); }
    public Set<String> getTags() { return tags; }
    public void setTags(Set<String> t) { this.tags = t; touch(); }
    public LocalDate getCreated() { return created; }
    public LocalDate getUpdated() { return updated; }
    public String getNotes() { return notes; }
    public void setNotes(String n) { this.notes = n; touch(); }

    private void touch() { this.updated = LocalDate.now(); }

    // ---------- Persistence helpers (TSV) ----------
    private static String esc(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n");
    }
    private static String unesc(String s) {
        if (s == null) return "";
        // simple unescape (order matters)
        return s.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\");
    }

    public String toTSV() {
        String dueStr = (due == null) ? "" : due.format(ISO);
        String tagsStr = String.join(",", tags);
        return String.join("\t",
            Integer.toString(id),
            esc(title),
            dueStr,
            priority.name(),
            Boolean.toString(done),
            esc(tagsStr),
            created.format(ISO),
            updated.format(ISO),
            esc(notes)
        );
    }

    public static Task fromTSV(String line) {
        String[] f = line.split("\t", -1); // keep empty fields
        if (f.length < 9) throw new IllegalArgumentException("Bad line: " + line);

        int id = Integer.parseInt(f[0]);
        Task t = new Task(id, unesc(f[1]));
        t.due = (f[2].isEmpty() ? null : LocalDate.parse(f[2], ISO));
        t.priority = Priority.valueOf(f[3]);
        t.done = Boolean.parseBoolean(f[4]);
        String tagStr = unesc(f[5]).trim();
        if (!tagStr.isEmpty()) {
            t.tags = Arrays.stream(tagStr.split(","))
                    .map(String::trim).filter(s -> !s.isEmpty())
                    .collect(Collectors.toCollection(LinkedHashSet::new));
        }
        t.created = LocalDate.parse(f[6], ISO);
        t.updated = LocalDate.parse(f[7], ISO);
        t.notes = unesc(f[8]);
        return t;
    }

    // ---------- Pretty printing ----------
    public String oneLine() {
        String dueStr = (due == null) ? "-" : due.format(ISO);
        String tagStr = tags.isEmpty() ? "-" : String.join(",", tags);
        String status = done ? "✓" : " ";
        return String.format("[%s] #%d %-10s %-10s %-12s %s",
                status, id, priority.name(), dueStr, tagStr, title);
    }
}
