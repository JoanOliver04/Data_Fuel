import { Heart } from "lucide-react";

import { useSettingsStore } from "@/stores/settings.store";

interface FavoriteButtonProps {
  stationId: number;
}

export function FavoriteButton({ stationId }: FavoriteButtonProps) {
  const favorites = useSettingsStore((s) => s.favorites);
  const toggleFavorite = useSettingsStore((s) => s.toggleFavorite);
  const isFavorite = favorites.includes(stationId);

  return (
    <button
      type="button"
      onClick={() => toggleFavorite(stationId)}
      aria-label={isFavorite ? "Quitar de favoritos" : "Añadir a favoritos"}
      aria-pressed={isFavorite}
      className="rounded-full p-1 transition-colors hover:bg-muted"
    >
      <Heart
        className={`h-4 w-4 transition-colors ${
          isFavorite ? "fill-red-500 text-red-500" : "text-muted-foreground"
        }`}
      />
    </button>
  );
}
