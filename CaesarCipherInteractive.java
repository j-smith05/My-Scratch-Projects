import java.util.Scanner;

public class CaesarCipherInteractive {

    /**
     * Encrypts a plaintext message using the Caesar Cipher.
     * @param plaintext The message to encrypt.
     * @param shift The number of positions to shift the letters.
     * @return The encrypted ciphertext.
     */
    public static String encrypt(String plaintext, int shift) {
        if (plaintext == null || plaintext.isEmpty()) {
            return plaintext;
        }

        // Normalize the shift to be between 0 and 25
        int effectiveShift = (shift % 26 + 26) % 26;
        
        StringBuilder ciphertext = new StringBuilder();

        for (int i = 0; i < plaintext.length(); i++) {
            char originalChar = plaintext.charAt(i);

            if (Character.isLetter(originalChar)) {
                
                char base = Character.isUpperCase(originalChar) ? 'A' : 'a';
                
                // 1. Convert to 0-25 index
                int originalIndex = originalChar - base;
                
                // 2. Apply the shift and wrap around
                int shiftedIndex = (originalIndex + effectiveShift) % 26;
                
                // 3. Convert back to character
                char encryptedChar = (char) (shiftedIndex + base);
                
                ciphertext.append(encryptedChar);
            } else {
                // Keep non-alphabetic characters unchanged
                ciphertext.append(originalChar);
            }
        }

        return ciphertext.toString();
    }

    /**
     * Decrypts a ciphertext message by shifting the letters back.
     * @param ciphertext The message to decrypt.
     * @param shift The original shift used for encryption.
     * @return The decrypted plaintext.
     */
    public static String decrypt(String ciphertext, int shift) {
        // Decrypting is equivalent to encrypting with a negative shift.
        return encrypt(ciphertext, -shift);
    }

    // --- Main Method with User Input ---
    public static void main(String[] args) {
        // Create a Scanner object for reading user input
        Scanner scanner = new Scanner(System.in);
        
        String message;
        int key = 0;
        
        System.out.println("--- Interactive Caesar Cipher Tool ---");

        // 1. Get the message from the user
        System.out.print("Enter the message (plaintext): ");
        message = scanner.nextLine();
        
        // 2. Get the shift value (key) from the user
        boolean validKey = false;
        while (!validKey) {
            System.out.print("Enter the shift value (e.g., 3): ");
            if (scanner.hasNextInt()) {
                key = scanner.nextInt();
                validKey = true;
            } else {
                System.out.println("Invalid input. Please enter an integer for the shift.");
                scanner.next(); // consume the invalid input
            }
        }
        
        // Clear the remaining newline character after reading the integer
        scanner.nextLine(); 

        System.out.println("\n------------------------------------");
        System.out.println("Your Message: " + message);
        System.out.println("Your Key: " + key);
        System.out.println("------------------------------------");

        // 3. Encrypt and display
        String encryptedMessage = encrypt(message, key);
        System.out.println("Encrypted Message (Ciphertext): " + encryptedMessage);

        // 4. Decrypt and display
        String decryptedMessage = decrypt(encryptedMessage, key);
        System.out.println("Decrypted Message (Plaintext): " + decryptedMessage);
        
        // Close the scanner
        scanner.close();
    }
}