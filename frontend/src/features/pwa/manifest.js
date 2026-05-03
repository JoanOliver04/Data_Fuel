export var pwaManifest = {
    name: "Data Fuel",
    short_name: "DataFuel",
    description: "Encuentra la gasolinera más rentable según precio, distancia y consumo.",
    theme_color: "#2563EB",
    background_color: "#F4F8FC",
    display: "standalone",
    orientation: "portrait",
    start_url: "/",
    scope: "/",
    lang: "es",
    categories: ["navigation", "travel", "utilities"],
    icons: [
        {
            src: "/pwa-64x64.png",
            sizes: "64x64",
            type: "image/png",
        },
        {
            src: "/pwa-192x192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any",
        },
        {
            src: "/pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any",
        },
        {
            src: "/maskable-icon-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
        },
    ],
};
