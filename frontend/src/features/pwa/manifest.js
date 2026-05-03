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
            src: "/icon.svg",
            sizes: "192x192 512x512",
            type: "image/svg+xml",
            purpose: "any",
        },
        {
            src: "/icon-maskable.svg",
            sizes: "192x192 512x512",
            type: "image/svg+xml",
            purpose: "maskable",
        },
    ],
};
