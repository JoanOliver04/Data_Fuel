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
            // Always activate the just-saved profile so the user immediately
            // sees its costs reflected in the search results.
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
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-lg items-center gap-3 px-4 py-3">
          <Link to="/" aria-label="Volver">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-lg font-semibold">Ajustes</h1>
        </div>
      </header>

      <main className="mx-auto max-w-lg space-y-6 px-4 py-6">
        {/* ── Mi Vehículo ────────────────────────────────────────────────── */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 font-semibold">
              <Car className="h-4 w-4" />
              Mi Vehículo
            </h2>
            {!showForm && (
              <Button size="sm" variant="outline" onClick={() => setShowForm(true)}>
                + Nuevo perfil
              </Button>
            )}
          </div>

          {/* Profile list */}
          {isLoading && (
            <p className="text-sm text-muted-foreground">Cargando perfiles…</p>
          )}

          {profiles && profiles.length > 0 && !showForm && (
            <div className="space-y-2">
              {profiles.map((profile) => (
                <Card
                  key={profile.id}
                  className={`transition-colors ${
                    activeVehicleProfileId === profile.id
                      ? "border-primary ring-1 ring-primary"
                      : "border-border"
                  }`}
                >
                  <CardContent className="flex items-center justify-between p-3">
                    <button
                      type="button"
                      className="flex flex-1 items-start gap-3 text-left"
                      onClick={() =>
                        setActiveVehicleProfileId(
                          activeVehicleProfileId === profile.id ? null : profile.id,
                        )
                      }
                    >
                      <div
                        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
                          activeVehicleProfileId === profile.id
                            ? "border-primary bg-primary"
                            : "border-muted-foreground"
                        }`}
                      >
                        {activeVehicleProfileId === profile.id && (
                          <Check className="h-3 w-3 text-primary-foreground" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium">{profile.name}</p>
                        <p className="text-xs text-muted-foreground">
                          Mixto {profile.fuel_consumption_mixed} L/100km ·{" "}
                          {profile.km_cost_per_km.toFixed(3)} €/km ·{" "}
                          {profile.tank_capacity_litres} L
                        </p>
                      </div>
                    </button>
                    <div className="flex items-center gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8"
                        aria-label="Editar perfil"
                        onClick={() => handleEdit(profile)}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        aria-label="Eliminar perfil"
                        onClick={() => handleDelete(profile.id)}
                        disabled={isMutating}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {profiles && profiles.length === 0 && !showForm && (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center gap-2 py-8 text-center">
                <Car className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm font-medium">Sin perfiles de vehículo</p>
                <p className="text-xs text-muted-foreground">
                  Crea uno para personalizar el Coste Real.
                </p>
                <Button size="sm" className="mt-2" onClick={() => setShowForm(true)}>
                  Crear perfil
                </Button>
              </CardContent>
            </Card>
          )}

          {showForm && (
            <Card>
              <CardContent className="p-4">
                <h3 className="mb-4 font-medium">
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
