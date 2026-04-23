import { Providers } from "@/app/providers";
import { AppRoutes } from "@/app/router";

export function App() {
  return (
    <Providers>
      <AppRoutes />
    </Providers>
  );
}
