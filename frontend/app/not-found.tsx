export default function NotFound() {
  return (
    <div className="h-full flex items-center justify-center px-6 text-center">
      <div>
        <p className="text-4xl mb-2">404</p>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Page not found.
        </p>
      </div>
    </div>
  );
}
