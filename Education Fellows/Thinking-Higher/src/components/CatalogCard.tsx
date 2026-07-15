import Link from "next/link";

interface CatalogCardProps {
  href: string;
  icon: string;
  title: string;
  description: string;
  badge: string;
  duration: string;
}

export default function CatalogCard({ href, icon, title, description, badge, duration }: CatalogCardProps) {
  return (
    <Link href={href} className="catalog-card" style={{ textDecoration: "none" }}>
      <div className="catalog-icon">{icon}</div>
      <div className="catalog-title">{title}</div>
      <div className="catalog-desc">{description}</div>
      <div className="catalog-meta">
        <span className="catalog-badge">{badge}</span>
        <span className="catalog-duration">{duration}</span>
      </div>
    </Link>
  );
}
