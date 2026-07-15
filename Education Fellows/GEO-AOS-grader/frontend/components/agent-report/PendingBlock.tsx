export default function PendingBlock() {
  return (
    <section className="rounded-2xl border border-neutral-200 bg-white px-6 py-8">
      <p className="font-semibold text-neutral-900">Browser Operability Scan</p>
      <p className="mt-2 max-w-lg text-sm text-neutral-500">
        Coming soon — we&apos;re adding headless browser analysis to check semantic HTML,
        ARIA attributes, stable URLs, keyboard navigation, and CAPTCHA presence.
      </p>
      <div className="mt-4 h-1.5 w-full rounded-full bg-neutral-100">
        <div className="h-1.5 w-0 rounded-full bg-neutral-200" />
      </div>
    </section>
  )
}
