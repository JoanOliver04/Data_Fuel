import { Card, CardContent } from "@/components/ui/card";

function Bone({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-muted ${className ?? ""}`} />;
}

export function RecommendationSkeleton() {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <Bone className="h-7 w-7 rounded-full" />
            <div className="space-y-2">
              <Bone className="h-4 w-32" />
              <Bone className="h-3 w-24" />
              <Bone className="h-3 w-40" />
            </div>
          </div>
          <div className="space-y-1">
            <Bone className="h-7 w-20" />
            <Bone className="ml-auto h-3 w-8" />
          </div>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2 border-t pt-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="space-y-1">
              <Bone className="h-3 w-12" />
              <Bone className="h-4 w-16" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
