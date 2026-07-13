"use client";
// Sticky chapter rail for the console. Scrollspy-driven; no persona theater.

export interface NavSection {
  id: string;
  label: string;
  group: string;
}

export function ConsoleNav({
  sections,
  active,
  onJump,
}: {
  sections: NavSection[];
  active: string;
  onJump: (id: string) => void;
}) {
  const groups = sections.reduce<Record<string, NavSection[]>>((acc, s) => {
    (acc[s.group] ??= []).push(s);
    return acc;
  }, {});

  return (
    <nav className="hidden w-52 shrink-0 lg:block">
      <div className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto pr-1">
        <div className="space-y-5">
          {Object.entries(groups).map(([group, items]) => (
            <div key={group}>
              <div className="mb-1.5 px-1 text-[0.6rem] font-semibold uppercase tracking-[0.14em] text-faint">
                {group}
              </div>
              <ul className="space-y-0.5">
                {items.map((s) => {
                  const on = active === s.id;
                  return (
                    <li key={s.id}>
                      <button
                        onClick={() => onJump(s.id)}
                        className={
                          "relative flex w-full items-center rounded-md py-1.5 pl-3 pr-2 text-left text-[0.82rem] transition " +
                          (on ? "text-text" : "text-muted hover:bg-surface2/40 hover:text-text")
                        }
                      >
                        <span
                          className={
                            "absolute left-0 top-1/2 h-3.5 w-[2px] -translate-y-1/2 rounded-full transition-all " +
                            (on ? "bg-accent opacity-100" : "opacity-0")
                          }
                        />
                        {s.label}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </nav>
  );
}
