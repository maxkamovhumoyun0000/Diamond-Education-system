export default function SignUpSuccessPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary to-accent flex items-center justify-center p-4">
      <div className="bg-background rounded-lg shadow-lg p-8 max-w-md w-full text-center">
        <h1 className="text-3xl font-bold text-primary mb-4">Account Created!</h1>
        <p className="text-foreground mb-4">
          Please check your email to confirm your account before signing in.
        </p>
        <a
          href="/auth/login"
          className="inline-block px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
        >
          Back to Sign In
        </a>
      </div>
    </div>
  );
}
