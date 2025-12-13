import java.util.Scanner;

public class TrainingTimeCalculator {

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.print("Enter ability (power, defense, magic, health, psychics, mobility): ");
        String ability = scanner.nextLine().toLowerCase();

        System.out.print("Enter number of training ticks: ");
        long times = scanner.nextLong();

        String result = calculateTrainingTime(ability, times);
        System.out.println("\nTraining Time:");
        System.out.println(result);

        scanner.close();
    }

    public static String calculateTrainingTime(String ability, long times) {
        double secondsPerTick;

        switch (ability) {
            case "power":
            case "defense":
            case "magic":
                secondsPerTick = 0.59;
                break;

            case "health":
            case "psychics":
                secondsPerTick = 0.71;
                break;

            case "mobility":
                secondsPerTick = 0.83;
                break;

            default:
                return "Invalid ability name.";
        }

        double totalSeconds = secondsPerTick * times;

        long hours = (long) (totalSeconds / 3600);
        long minutes = (long) ((totalSeconds % 3600) / 60);
        double seconds = totalSeconds % 60;

        return String.format("%d hours, %d minutes, %.2f seconds",hours, minutes, seconds);
    }
}
