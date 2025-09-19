import java.util.Scanner;

public class CaesarCipher {

    // Encrypts text using Caesar's Cipher
    public static String encrypt(String text, int shift) {
        StringBuilder result = new StringBuilder();

        for (char c : text.toCharArray()) {
            if (Character.isUpperCase(c)) {
                result.append((char) ((c - 'A' + shift + 26) % 26 + 'A'));
            } else if (Character.isLowerCase(c)) {
                result.append((char) ((c - 'a' + shift + 26) % 26 + 'a'));
            } else {
                result.append(c); // Non-alphabetic characters remain unchanged
            }
        }
        return result.toString();
    }

    // Decrypts text by reversing the shift
    public static String decrypt(String text, int shift) {
        return encrypt(text, -shift);
    }

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.println("Caesar Cipher Program");
        System.out.print("Enter text: ");
        String text = scanner.nextLine();

        System.out.print("Enter shift (e.g., 3): ");
        int shift = scanner.nextInt();

        String encrypted = encrypt(text, shift);
        String decrypted = decrypt(encrypted, shift);

        System.out.println("\nEncrypted: " + encrypted);
        System.out.println("Decrypted: " + decrypted);

        scanner.close();
    }
}
