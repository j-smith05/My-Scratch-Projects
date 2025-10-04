import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

public class FileTaskRepository {
    private final Path file;

    public FileTaskRepository(String filename) {
        this.file = Paths.get(filename);
        try {
            if (Files.notExists(file)) {
                Files.createDirectories(file.getParent() == null ? Paths.get(".") : file.getParent());
                Files.createFile(file);
            }
        } catch (IOException e) {
            throw new RuntimeException("Cannot initialize storage: " + filename, e);
        }
    }

    public List<Task> loadAll() {
        try {
            return Files.readAllLines(file).stream()
                    .filter(s -> !s.trim().isEmpty())
                    .map(Task::fromTSV)
                    .collect(Collectors.toCollection(ArrayList::new));
        } catch (IOException e) {
            throw new RuntimeException("Read failed", e);
        }
    }

    public void saveAll(List<Task> tasks) {
        try {
            List<String> lines = tasks.stream().map(Task::toTSV).toList();
            Files.write(file, lines, StandardOpenOption.TRUNCATE_EXISTING);
        } catch (IOException e) {
            throw new RuntimeException("Write failed", e);
        }
    }

    public int nextId(List<Task> tasks) {
        return tasks.stream().mapToInt(Task::getId).max().orElse(0) + 1;
    }
}
