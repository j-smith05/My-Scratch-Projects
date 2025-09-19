import java.util.Scanner;

/**
 * This program is designed to gather user input
 * of certain text, and then ask for a shift
 * and then shift the text accordingly
 * i.e HELLO by 3 becomes KHOOR
 * 
 * @author Jacob Smith
 **/

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
        System.out.print("Enter text (Encrypted or Decrypted): ");
        String text = scanner.nextLine();

        System.out.print("Enter shift (e.g., 3 to Encrypt & -3 to Decrypt): ");
        int shift = scanner.nextInt();

        String encrypted = encrypt(text, shift);
        String decrypted = decrypt(encrypted, shift);

        System.out.println("\nEncrypted: " + encrypted);
        System.out.println("Decrypted: " + decrypted);

        scanner.close();
    }
}
