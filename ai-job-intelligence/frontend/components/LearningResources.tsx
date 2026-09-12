"use client";

/**
 * Places to actually learn a skill the posting asked for.
 *
 * Loaded separately from the analysis because it reaches third-party APIs:
 * the page must be readable the instant it opens, with this arriving when it
 * arrives. If every source is down the panel says so rather than rendering an
 * empty box that implies nothing exists.
 */

import { useEffect, useState } from "react";
import {
  FaBook,
  FaCode,
  FaNewspaper,
  FaComments,
  FaGraduationCap,
  FaArrowUpRightFromSquare,
} from "react-icons/fa6";

import { apiCall } from "@/components/api";

interface Resource {
  title: string;
  url: string;
  source: string;
  kind: "docs" | "course" | "repo" | "article" | "discussion";
  description: string;
  signal: string;
}

interface SkillBlock {
  skill: string;
  degraded: boolean;
  resources: Resource[];
}

const KIND_ICON = {
  docs: FaBook,
  course: FaGraduationCap,
  repo: FaCode,
  article: FaNewspaper,
  discussion: FaComments,
} as const;

const KIND_LABEL = {
  docs: "Documentation",
  course: "Course",
  repo: "Repository",
  article: "Article",
  discussion: "Discussion",
} as const;

export default function LearningResources({ skills }: { skills: string[] }) {
  const [blocks, setBlocks] = useState<SkillBlock[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "failed">("loading");
  const [active, setActive] = useState(0);

  const wanted = skills.filter(Boolean).slice(0, 4);
  const key = wanted.join(",");

  useEffect(() => {
    // Nothing to look up. The component renders null below, so there is no
    // state worth setting here.
    if (!key) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiCall(
          `/api/learning-resources?skills=${encodeURIComponent(key)}`,
        );
        if (!res.ok) throw new Error("lookup failed");
        const data = await res.json();
        if (cancelled) return;
        setBlocks(data.skills ?? []);
        setState("ready");
      } catch {
        if (!cancelled) setState("failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [key]);

  if (!key) return null;

  if (state === "loading") {
    return (
      <section className="card">
        <h2 className="section-title">Where to learn this</h2>
        <p className="meta mt-1">Looking for current resources…</p>
        <div className="mt-5 space-y-2.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-14 rounded-md bg-neutral-800/50 animate-pulse"
            />
          ))}
        </div>
      </section>
    );
  }

  if (state === "failed") {
    return (
      <section className="card">
        <h2 className="section-title">Where to learn this</h2>
        <p className="body-text mt-2">
          Resource lookup is unavailable right now. Your analysis above is
          unaffected.
        </p>
      </section>
    );
  }

  const current = blocks[active];

  return (
    <section className="card">
      <h2 className="section-title">Where to learn this</h2>
      <p className="meta mt-1">
        Current documentation, projects and discussions for the skills this
        posting wanted.
      </p>

      {/* One skill at a time: four stacked lists is a wall, not a resource. */}
      {blocks.length > 1 && (
        <div className="flex flex-wrap gap-2 mt-5">
          {blocks.map((b, i) => (
            <button
              key={b.skill}
              type="button"
              onClick={() => setActive(i)}
              aria-pressed={i === active}
              className={
                i === active
                  ? "px-3 py-1.5 rounded-md text-[0.8125rem] font-medium bg-neutral-100 text-neutral-950"
                  : "px-3 py-1.5 rounded-md text-[0.8125rem] font-medium bg-neutral-800/60 text-neutral-300 border border-neutral-800 hover:border-neutral-700 transition-colors"
              }
            >
              {b.skill}
            </button>
          ))}
        </div>
      )}

      {current?.degraded && (
        <p className="body-text mt-4">
          Could not reach the resource sources for {current.skill}. Try again in
          a moment.
        </p>
      )}

      <div className="mt-5 space-y-2">
        {(current?.resources ?? []).map((r) => {
          const Icon = KIND_ICON[r.kind] ?? FaBook;
          return (
            <a
              key={r.url}
              href={r.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex gap-3.5 rounded-md border border-neutral-800 p-3.5
                         hover:border-neutral-700 hover:bg-neutral-800/30 transition-colors"
            >
              <Icon className="w-4 h-4 text-neutral-500 mt-0.5 shrink-0 group-hover:text-neutral-300 transition-colors" />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2 flex-wrap">
                  <span className="item-title group-hover:text-white transition-colors">
                    {r.title}
                  </span>
                  <FaArrowUpRightFromSquare className="w-2.5 h-2.5 text-neutral-600 group-hover:text-neutral-400 transition-colors" />
                </div>
                {r.description && (
                  <p className="text-[0.8125rem] text-neutral-400 mt-1 line-clamp-2">
                    {r.description}
                  </p>
                )}
                <p className="meta mt-1.5">
                  {KIND_LABEL[r.kind] ?? r.kind} · {r.source}
                  {r.signal ? ` · ${r.signal}` : ""}
                </p>
              </div>
            </a>
          );
        })}

        {current && current.resources.length === 0 && !current.degraded && (
          <p className="body-text">
            Nothing specific found for {current.skill}. Searching for it by name
            plus &ldquo;tutorial&rdquo; is usually enough to start.
          </p>
        )}
      </div>
    </section>
  );
}
