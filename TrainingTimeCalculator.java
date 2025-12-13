import java.util.Scanner;

/**
 * Calculates how long it takes to train an ability a given number of times.
 * Allows abbreviations and user-defined training speeds.
 * @author jsmith-05
 */
public class TrainingTimeCalculator {

    /**
     * Runs the program and handles user input.
     * @param args command-line arguments (not used)
     */
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        String ability = promptForAbility(scanner);

        System.out.print("Enter seconds per training tick: ");
        double secondsPerTick = scanner.nextDouble();

        System.out.print("Enter number of training ticks: ");
        long times = scanner.nextLong();

        String result = calculateTrainingTime(secondsPerTick, times);

        System.out.println("\nTraining Time for " + ability + ":");
        System.out.println(result);

        scanner.close();
    }

    /**
     * Prompts the user until a valid ability or abbreviation is entered.
     * @param scanner the Scanner used to read user input
     * @return the full ability name
     */
    private static String promptForAbility(Scanner scanner) {
        while (true) {
            System.out.print(
                "Enter ability (power/pwr, defense/def, magic/mag, " +
                "health/hp, psychics/psy, mobility/mob): "
            );

            String input = scanner.nextLine().trim().toLowerCase();
            String normalized = normalizeAbility(input);

            if (normalized != null) {
                return normalized;
            }

            System.out.println("Invalid ability. Please try again.\n");
        }
    }

    /**
     * Converts an ability name or abbreviation into its full form.
     * @param input the user-entered ability string
     * @return the full ability name, or null if invalid
     */
    private static String normalizeAbility(String input) {
        switch (input) {
            case "power":
            case "pwr":
                return "power";

            case "defense":
            case "def":
                return "defense";

            case "magic":
            case "mag":
                return "magic";

            case "health":
            case "hp":
                return "health";

            case "psychics":
            case "psy":
                return "psychics";

            case "mobility":
            case "mob":
                return "mobility";

            default:
                return null;
        }
    }

    /**
     * Calculates and formats the total training time.
     *
     * @param secondsPerTick seconds required per training tick
     * @param times number of training ticks
     * @return formatted training time string
     */
    public static String calculateTrainingTime(double secondsPerTick, long times) {
        if (secondsPerTick <= 0 || times < 0) {
            return "Invalid numeric input.";
        }

        long totalSeconds = (long) Math.floor(secondsPerTick * times);

        long hours = totalSeconds / 3600;
        long minutes = (totalSeconds % 3600) / 60;
        long seconds = totalSeconds % 60;

        return hours + " hours, " + minutes + " minutes, " + seconds + " seconds";
    }
}
