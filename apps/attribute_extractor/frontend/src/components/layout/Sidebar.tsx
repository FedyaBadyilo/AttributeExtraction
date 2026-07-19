export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand__title">Ассистент ТЗ</div>
        <div className="brand__subtitle">Извлечение атрибутов</div>
      </div>
      <nav className="sidebar-nav">
        <button className="sidebar-nav__item sidebar-nav__item--active" type="button">
          <span className="nav-icon">◫</span>
          Задачи
        </button>
      </nav>
    </aside>
  );
}
