import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

public class TodoApp {

    private static final String STORE = "tasks.tsv";

    public static void main(String[] args) {
        FileTaskRepository repo = new FileTaskRepository(STORE);
        List<Task> tasks = repo.loadAll();

        if (args.length == 0) {
            printHelp();
            return;
        }

        String cmd = args[0].toLowerCase(Locale.ROOT);
        switch (cmd) {
            case "add" -> {
                Map<String,String> flags = parseFlags(Arrays.copyOfRange(args, 1, args.length));
                String title = flags.getOrDefault("_", "").trim();
                if (title.isEmpty()) {
                    System.out.println("Usage: add <title> [-d YYYY-MM-DD] [-p LOW|MED|HIGH] [-t tag1,tag2] [-n notes]");
                    return;
                }
                int id = new FileTaskRepository(STORE).nextId(tasks);
                Task t = new Task(id, title);

                if (flags.containsKey("d")) t.setDue(LocalDate.parse(flags.get("d")));
                if (flags.containsKey("p")) t.setPriority(Task.Priority.valueOf(flags.get("p").toUpperCase()));
                if (flags.containsKey("t")) t.setTags(new LinkedHashSet<>(Arrays.stream(flags.get("t").split(","))
                        .map(String::trim).filter(s->!s.isEmpty()).toList()));
                if (flags.containsKey("n")) t.setNotes(flags.get("n"));

                tasks.add(t);
                repo.saveAll(tasks);
                System.out.println("Added: " + t.oneLine());
            }
            case "list" -> {
                boolean showAll = hasFlag(args, "--all");
                String sort = getOpt(args, "--sort").orElse("due");

                List<Task> view = new ArrayList<>(tasks);
                if (!showAll) {
                    view = view.stream().filter(t -> !t.isDone()).collect(Collectors.toList());
                }

                Comparator<Task> byDue = Comparator.comparing(t -> Optional.ofNullable(t.getDue()).orElse(LocalDate.MAX));
                Comparator<Task> byPriority = Comparator.comparing(Task::getPriority);
                if ("priority".equalsIgnoreCase(sort)) view.sort(byPriority.thenComparing(byDue));
                else view.sort(byDue.thenComparing(byPriority));

                if (view.isEmpty()) { System.out.println("(no tasks)"); return; }
                view.forEach(t -> System.out.println(t.oneLine()));
            }
            case "done" -> {
                if (args.length < 2) { System.out.println("Usage: done <id>"); return; }
                int id = Integer.parseInt(args[1]);
                tasks.stream().filter(t -> t.getId() == id).findFirst().ifPresentOrElse(t -> {
                    t.setDone(true);
                    repo.saveAll(tasks);
                    System.out.println("Completed: " + t.oneLine());
                }, () -> System.out.println("No task id " + id));
            }
            case "delete" -> {
                if (args.length < 2) { System.out.println("Usage: delete <id>"); return; }
                int id = Integer.parseInt(args[1]);
                boolean removed = tasks.removeIf(t -> t.getId() == id);
                if (removed) { repo.saveAll(tasks); System.out.println("Deleted #" + id); }
                else System.out.println("No task id " + id);
            }
            case "find" -> {
                if (args.length < 2) { System.out.println("Usage: find <query>"); return; }
                String q = String.join(" ", Arrays.copyOfRange(args, 1, args.length)).toLowerCase();
                List<Task> matches = tasks.stream()
                        .filter(t -> (t.getTitle()+" "+t.getNotes()).toLowerCase().contains(q))
                        .collect(Collectors.toList());
                if (matches.isEmpty()) System.out.println("(no matches)");
                else matches.forEach(t -> System.out.println(t.oneLine()));
            }
            case "today" -> {
                LocalDate today = LocalDate.now();
                tasks.stream().filter(t -> !t.isDone() && today.equals(t.getDue()))
                        .sorted(Comparator.comparing(Task::getPriority))
                        .forEach(t -> System.out.println(t.oneLine()));
            }
            case "overdue" -> {
                LocalDate today = LocalDate.now();
                List<Task> od = tasks.stream()
                        .filter(t -> !t.isDone() && t.getDue()!=null && t.getDue().isBefore(today))
                        .sorted(Comparator.comparing(Task::getDue))
                        .toList();
                if (od.isEmpty()) System.out.println("(none overdue)");
                else od.forEach(t -> System.out.println(t.oneLine()));
            }
            case "help" -> printHelp();
            default -> {
                if (!List.of("add","list","done","delete","find","today","overdue","help").contains(cmd)) {
                    System.out.println("Unknown command: " + cmd);
                    printHelp();
                }
            }
        }
    }

    // ------- tiny flag parser -------
    // Collects: positional (under key "_") and short flags: -d, -p, -t, -n
    private static Map<String,String> parseFlags(String[] args) {
        Map<String,String> map = new LinkedHashMap<>();
        StringBuilder positional = new StringBuilder();
        for (int i=0; i<args.length; i++) {
            String a = args[i];
            if (a.startsWith("-") && a.length()==2 && i+1<args.length && !args[i+1].startsWith("-")) {
                map.put(a.substring(1), args[++i]);
            } else if (a.startsWith("--")) {
                // long flags handled separately by helpers; ignore here
            } else {
                if (positional.length()>0) positional.append(" ");
                positional.append(a);
            }
        }
        map.put("_", positional.toString());
        return map;
    }
    private static boolean hasFlag(String[] args, String flag) {
        for (String a : args) if (a.equalsIgnoreCase(flag)) return true;
        return false;
    }
    private static Optional<String> getOpt(String[] args, String flag) {
        for (int i=0;i<args.length-1;i++) if (args[i].equalsIgnoreCase(flag)) return Optional.of(args[i+1]);
        return Optional.empty();
    }

    private static void printHelp() {
        System.out.println("""
        To-Do CLI
          add <title> [-d YYYY-MM-DD] [-p LOW|MED|HIGH] [-t tag1,tag2] [-n notes]
          list [--all] [--sort due|priority]
          done <id>
          delete <id>
          find <query>
          today
          overdue
          help

        Examples:
          add "Write OS paper" -d 2025-10-12 -p HIGH -t school,cs -n "2 pages + citations"
          list --sort priority
          done 3
          find paper
        """);
    }
}

