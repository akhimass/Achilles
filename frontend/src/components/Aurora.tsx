// Living green aurora behind the whole app. Pure CSS (transform-only drift), fixed
// and non-interactive, subtle enough to keep text crisp. Frozen under reduced-motion.
export function Aurora() {
  return (
    <div className="aurora" aria-hidden>
      <div className="aurora-blob aurora-a" />
      <div className="aurora-blob aurora-b" />
      <div className="aurora-blob aurora-c" />
    </div>
  );
}
