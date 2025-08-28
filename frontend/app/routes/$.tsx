export async function loader() {
  // Handle Chrome DevTools request specifically
  if (typeof window !== 'undefined' && window.location.pathname.includes('/.well-known/appspecific/com.chrome.devtools.json')) {
    return new Response('{}', {
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  // For other unmatched routes, return 404
  return new Response('Not Found', { status: 404 });
}

export default function CatchAll() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-zinc-900 mb-2">Page Not Found</h1>
        <p className="text-zinc-600 mb-4">The page you're looking for doesn't exist.</p>
        <a href="/" className="text-zinc-900 hover:text-zinc-700 underline">
          Go back home
        </a>
      </div>
    </div>
  );
} 