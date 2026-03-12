export default function TabBar({ tabs, activeTab, onTabClick }) {
  return (
    <div className="tab-bar" role="tablist">
      {tabs.map(({ name, label }) => (
        <button
          key={name}
          className={`tab${activeTab === name ? ' active' : ''}`}
          role="tab"
          aria-selected={activeTab === name}
          onClick={() => onTabClick(name)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
