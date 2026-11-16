import "./styles.css";
export const metadata = {
  title: "Crosspoints",
  description: "Your saved moving averages",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "Crosspoints",
    statusBarStyle: "black-translucent",
  },
  icons: { apple: "/icon-180.png", icon: "/app-icon.png" },
};
export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0B1116",
};
export default function Layout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
