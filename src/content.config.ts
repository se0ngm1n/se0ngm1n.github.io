import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const projects = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/projects' }),
  schema: z.object({
    title: z.string(),
    subtitle: z.string().optional(),
    period: z.string(),
    category: z.string(),
    summary: z.string(),
    technologies: z.array(z.string()),
    outcomes: z.array(z.string()).default([]),
    order: z.number().default(99),
  }),
});

const study = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/study' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    category: z.string(),
    summary: z.string(),
    tags: z.array(z.string()).default([]),
    thumbnail: z.string().optional(),
  }),
});

const life = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/life' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    category: z.string(),
    summary: z.string().optional(),
    cover: z.string().optional(),
    gallery: z.array(z.string()).default([]),
  }),
});

export const collections = { projects, study, life };
