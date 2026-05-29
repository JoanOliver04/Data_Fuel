import { useState } from "react";

import { ArrowLeft, Car, Check, Pencil, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { VehicleProfileForm } from "@/features/vehicle-profile/VehicleProfileForm";
import {
  useCreateVehicleProfile,
  useDeleteVehicleProfile,
  useUpdateVehicleProfile,
  useVehicleProfiles,
} from "@/features/vehicle-profile/hooks";
import type { VehicleProfile, VehicleProfileCreate } from "@/features/vehicle-profile/types";
import { ApiError } from "@/lib/api-client";
import { useSettingsStore } from "@/stores/settings.store";
import { useToastStore } from "@/stores/toast.store";
import { cn } from "@/lib/utils";

export function Settings() {
  const { activeVehicleProfileId, setActiveVehicleProfileId } = useSettingsStore();
  const showToast = useToastStore((s) => s.show);
  const { data: profiles, isLoading } = useVehicleProfiles();
  const createMutation = useCreateVehicleProfile();
  const updateMutation = useUpdateVehicleProfile();
  const deleteMutation = useDeleteVehicleProfile();

  const [showForm, setShowForm] = useState(false);
  const [editingProfile, setEditingProfile] = useState<VehicleProfile | null>(null);

  function handleSaveError(error: unknown) {
    const message =
      error instanceof ApiError
        ? `No se pudo guardar el perfil (${error.status})`
        : "No se pudo guardar el perfil";
    showToast(message, "error");
  }

  function handleSave(data: VehicleProfileCreate) {
    if (editingProfile) {
      updateMutation.mutate(
        { id: editingProfile.id, data },
        {
          onSuccess: (updated) => {
            setActiveVehicleProfileId(updated.id);
            setEditingProfile(null);
            setShowForm(false);
            showToast(`Perfil "${updated.name}" guardado`, "success");
          },
          onError: handleSaveError,
        },
      );
    } else {
      createMutation.mutate(data, {
        onSuccess: (created) => {
          setActiveVehicleProfileId(created.id);
          setShowForm(false);
          showToast(`Perfil "${created.name}" creado`, "success");
        },
        onError: handleSaveError,
      });
    }
  }

  function handleEdit(profile: VehicleProfile) {
    setEditingProfile(profile);
    setShowForm(true);
  }

  function handleDelete(id: number) {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        if (activeVehicleProfileId === id) setActiveVehicleProfileId(null);
      },
    });
  }

  function handleCancel() {
    setEditingProfile(null);
    setShowForm(false);
  }

  const isMutating =
    createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  return (
    <div className="min-h-dvh bg-background pb-20 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300 lg:pb-0">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur-xl supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto flex max-w-lg items-center gap-3 px-4 py-3">
          <Link to="/" aria-label="Volver">
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-lg text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-lg font-extrabold tracking-tight">Ajustes</h1>
        </div>
      </header>

      <main className="mx-auto max-w-lg space-y-6 px-4 py-6">
        {/* ── Mi Vehículo ─────────────────────────────────────────────────── */}
        <section>
          {/* Section header */}
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
                <Car className="h-4 w-4 text-primary" />
              </div>
              <h2 className="font-semibold">Mi Vehículo</h2>
            </div>
            {!showForm && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowForm(true)}
                className="h-8 rounded-lg text-xs font-semibold"
              >
                + Nuevo perfil
              </Button>
            )}
          </div>

          {/* Loading */}
          {isLoading && (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="h-20 animate-pulse rounded-xl bg-muted" />
              ))}
            </div>
          )}

          {/* Profile list */}
          {profiles && profiles.length > 0 && !showForm && (
            <div className="space-y-2">
              {profiles.map((profile) => {
                const isActive = activeVehicleProfileId === profile.id;
                return (
                  <Card
                    key={profile.id}
                    className={cn(
                      "transition-all duration-150",
                      isActive
                        ? "border-primary/50 bg-primary/5 shadow-sm ring-2 ring-primary/15"
                        : "border-border hover:border-primary/30 hover:shadow-sm",
                    )}
                  >
                    <CardContent className="flex items-center justify-between p-3">
                      <button
                        type="button"
                        className="flex flex-1 items-start gap-3 text-left"
                        onClick={() =>
                          setActiveVehicleProfileId(isActive ? null : profile.id)
                        }
                      >
                        {/* Radio circle */}
                        <div
                          className={cn(
                            "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-all",
                            isActive
                              ? "border-primary bg-primary"
                              : "border-muted-foreground/40",
                          )}
                        >
                          {isActive && <Check className="h-3 w-3 text-primary-foreground" />}
                        </div>

                        {/* Profile info */}
                        <div>
                          <p className={cn("font-semibold", isActive && "text-primary")}>
                            {profile.name}
                          </p>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {profile.fuel_consumption_mixed} L/100km
                            <span className="mx-1.5 text-border">·</span>
                            {profile.km_cost_per_km.toFixed(3)} €/km
                            <span className="mx-1.5 text-border">·</span>
                            {profile.tank_capacity_litres} L
                          </p>
                        </div>
                      </button>

                      {/* Actions */}
                      <div className="flex items-center gap-0.5">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 rounded-lg text-muted-foreground hover:text-foreground"
                          aria-label="Editar perfil"
                          onClick={() => handleEdit(profile)}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 rounded-lg text-muted-foreground hover:text-destructive"
                          aria-label="Eliminar perfil"
                          onClick={() => handleDelete(profile.id)}
                          disabled={isMutating}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {/* Empty state */}
          {profiles && profiles.length === 0 && !showForm && (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
                  <Car className="h-7 w-7 text-muted-foreground" />
                </div>
                <div>
                  <p className="font-semibold">Sin perfiles de vehículo</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Crea uno para personalizar el Coste Real.
                  </p>
                </div>
                <Button size="sm" className="mt-1 rounded-lg" onClick={() => setShowForm(true)}>
                  Crear perfil
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Form */}
          {showForm && (
            <Card>
              <CardContent className="p-4">
                <h3 className="mb-4 font-semibold">
                  {editingProfile ? `Editar: ${editingProfile.name}` : "Nuevo perfil"}
                </h3>
                <VehicleProfileForm
                  initial={editingProfile ?? undefined}
                  onSave={handleSave}
                  onCancel={handleCancel}
                  isSaving={isMutating}
                />
              </CardContent>
            </Card>
          )}
        </section>
      </main>
    </div>
  );
}
