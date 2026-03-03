namespace SampleCode
{
    /// <summary>
    /// Provides basic arithmetic and mathematical utility operations.
    /// </summary>
    public class MathHelper
    {
        private readonly int _precision;

        public MathHelper(int precision = 2)
        {
            _precision = precision;
        }

        public int Add(int a, int b)
        {
            return a + b;
        }

        public int Subtract(int a, int b)
        {
            return a - b;
        }

        public double Multiply(double a, double b)
        {
            return Math.Round(a * b, _precision);
        }

        public double Divide(double a, double b)
        {
            if (b == 0)
                throw new DivideByZeroException("Cannot divide by zero.");
            return Math.Round(a / b, _precision);
        }

        public double Power(double baseValue, int exponent)
        {
            return Math.Round(Math.Pow(baseValue, exponent), _precision);
        }

        public bool IsPrime(int n)
        {
            if (n < 2) return false;
            for (int i = 2; i <= Math.Sqrt(n); i++)
            {
                if (n % i == 0) return false;
            }
            return true;
        }

        public int Factorial(int n)
        {
            if (n < 0)
                throw new ArgumentException("Factorial is not defined for negative numbers.");
            if (n == 0) return 1;
            return n * Factorial(n - 1);
        }

        public double Average(IEnumerable<double> values)
        {
            var list = values.ToList();
            if (list.Count == 0)
                throw new ArgumentException("Cannot compute average of an empty collection.");
            return Math.Round(list.Average(), _precision);
        }
    }

    /// <summary>
    /// Represents a 2D point and supports basic geometric operations.
    /// </summary>
    public class Point2D
    {
        public double X { get; }
        public double Y { get; }

        public Point2D(double x, double y)
        {
            X = x;
            Y = y;
        }

        public double DistanceTo(Point2D other)
        {
            double dx = X - other.X;
            double dy = Y - other.Y;
            return Math.Round(Math.Sqrt(dx * dx + dy * dy), 4);
        }

        public Point2D Translate(double dx, double dy)
        {
            return new Point2D(X + dx, Y + dy);
        }

        public override string ToString()
        {
            return $"({X}, {Y})";
        }
    }
}
