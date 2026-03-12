export default function RefreshIndicator({ loading }) {
  if (!loading) return null;

  return (
    <div className="refresh-indicator" data-testid="refresh-indicator">
      <span className="refresh-spinner" />
    </div>
  );
}
