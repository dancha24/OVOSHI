/**
 * Иконки модерации: пути как в Lucide (ISC), без пакета lucide-react — чтобы Docker/Vite
 * не требовал лишний npm install в контейнере.
 * @see https://lucide.dev/icons/ (sport-shoe, brick-wall, info)
 */
function IconBase({ size = 18, strokeWidth = 2, children, ...rest }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...rest}
    >
      {children}
    </svg>
  )
}

/** Исключить из клана — sport-shoe (Lucide). */
export function IconKick(props) {
  return (
    <IconBase {...props}>
      <path d="m15 10.42 4.8-5.07" />
      <path d="M19 18h3" />
      <path d="M9.5 22 21.414 9.415A2 2 0 0 0 21.2 6.4l-5.61-4.208A1 1 0 0 0 14 3v2a2 2 0 0 1-1.394 1.906L8.677 8.053A1 1 0 0 0 8 9c-.155 6.393-2.082 9-4 9a2 2 0 0 0 0 4h14" />
    </IconBase>
  )
}

/** Забанить — brick-wall (Lucide). */
export function IconBrickBan(props) {
  return (
    <IconBase {...props}>
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M12 9v6" />
      <path d="M16 15v6" />
      <path d="M16 3v6" />
      <path d="M3 15h18" />
      <path d="M3 9h18" />
      <path d="M8 15v6" />
      <path d="M8 3v6" />
    </IconBase>
  )
}

/** Подробнее — info (Lucide). */
export function IconInfo(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4" />
      <path d="M12 8h.01" />
    </IconBase>
  )
}
