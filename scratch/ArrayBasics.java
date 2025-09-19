public class ArrayBasics 
{
    /**
     *
     * This program was for my CS 121,
     * where i made an area of 5 values
     * and then had a for loop to print 
     * each of them out.
     * 
     * @author Jacob Smith 
     **/
    public static void main(String[] args)
    {
        double[] scores = new double[5]; // Array with my values 
        scores[0] = 98.5;
        scores[1] = 87.0;
        scores[2] = 92.5;
        scores[3] = 85.0;
        scores[4] = 90.0;

        for ( int i = 0; i < scores.length; i++ ) // For loop to print each of my values in the area in a print statement
        {
            System.out.println("The score at index " + i + " is: " + scores[i]);
        }

        for (double score: scores) // For loop to store each of my values in my "scores" array and then print them out
        {
            System.out.println("The score is: " + score);
        }
    }

}
    
