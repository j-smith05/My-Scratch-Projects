public class ArrayBasics 
{

    public static void main(String[] args)
    {
        double[] scores = new double[5];
        scores[0] = 98.5;
        scores[1] = 87.0;
        scores[2] = 92.5;
        scores[3] = 85.0;
        scores[4] = 90.0;

        for ( int i = 0; i < scores.length; i++ )
        {
            System.out.println("The score at index " + i + " is: " + scores[i]);
        }

        for (double score: scores)
        {
            System.out.println("The score is: " + score);
        }
    }

}
    
