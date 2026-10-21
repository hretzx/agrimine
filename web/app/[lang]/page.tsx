"use client";

import { AppShell } from "@/components/farm/app-shell";
import { GreetingHeader } from "@/components/home/header";
import { Hero } from "@/components/home/hero";
import { DoctorCard, PlanB, TopCrops } from "@/components/home/crops";
import { AccuracyCard, FarmsCard, GainCard, NeedsCard, PatternsCard } from "@/components/home/insights";
import { Stats } from "@/components/home/stats";
import { ErrorState, Loading } from "@/components/ui/states";
import { useCurrentCheck } from "@/lib/data";
import { Suspense } from "react";

function HomeBody() {
  const { check, loading, empty, error } = useCurrentCheck();
  if (error) return <ErrorState />;
  if (loading) return <Loading className="h-96" />;
  return (
    <>
      <div className="mb-3 grid grid-cols-1 gap-3 lg:grid-cols-[1.35fr_1fr_1.05fr]">
        <Hero check={check} empty={empty} />
        <TopCrops check={check} />
        <DoctorCard check={check} />
      </div>
      <div className="mb-3 grid grid-cols-1 gap-3 lg:grid-cols-[1fr_1.25fr_1.15fr]">
        <PlanB check={check} />
        <FarmsCard check={check} />
        <NeedsCard check={check} />
      </div>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <GainCard />
        <PatternsCard />
        <AccuracyCard />
      </div>
    </>
  );
}

export default function Home() {
  return (
    <AppShell active="home">
      <GreetingHeader />
      <Stats />
      <Suspense fallback={<Loading className="h-96" />}>
        <HomeBody />
      </Suspense>
    </AppShell>
  );
}
