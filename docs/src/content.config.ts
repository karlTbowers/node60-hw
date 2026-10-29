// Content collections: the docs pages plus the architecture's facts as data
// (handbook chapter 08). Every cross-reference is a `reference()`; src/lib/data.ts
// resolves them all at build time and fails the build on an unknown ID.
import { defineCollection, reference } from 'astro:content';
import { file, glob } from 'astro/loaders';
import { z } from 'astro/zod';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

const date = z.coerce.date();

const requirements = defineCollection({
	loader: file('src/data/requirements.yaml'),
	schema: z.object({
		id: z.string().regex(/^REQ-[A-Z]+-\d{3}$/),
		// basis: the design-requirement list; parameter: the parameter table
		group: z.enum(['basis', 'parameter']),
		parameter: z.string().optional(),
		text: z.string(),
		consequence: z.string().optional(),
		rationale: z.string().optional(),
		page: z.string().optional(),
		verified_by: z.array(reference('gates')).default([]),
	}),
});

// A dated price/stock observation (handbook chapter 03): never a quote.
// `approx` marks figures the source recorded as approximate (≈).
const observation = z.object({
	date,
	source: z.string(),
	prices: z
		.array(z.object({ qty: z.string(), usd: z.number(), approx: z.boolean().default(false) }))
		.default([]),
	stock: z.number().int().optional(),
	stock_approx: z.boolean().default(false),
	note: z.string().optional(),
});

const parts = defineCollection({
	loader: file('src/data/parts.yaml'),
	schema: z.object({
		// The MPN, or a TBD-… placeholder while the exact orderable code is open
		id: z.string(),
		mpn: z.string().nullable(),
		manufacturer: z.string().nullable(),
		qty: z.number().int(),
		label: z.string().optional(),
		function: z.string(),
		subsystem: z.enum(['power', 'compute', 'supervision', 'network', 'outputs', 'temperature', 'harness', 'firmware']),
		status: z.enum(['selected', 'plan-of-record', 'locked', 'alternative', 'future', 'open']),
		decision_note: z.string(),
		supply_note: z.string().optional(),
		observations: z.array(observation).default([]),
		second_source: z.string().nullable().default(null),
		decisions: z.array(reference('decisions')).default([]),
		library: z
			.string()
			.regex(/^DropOut_[A-Za-z0-9_]+:.+$/)
			.nullable()
			.default(null),
	}),
});

const gates = defineCollection({
	loader: file('src/data/gates.yaml'),
	schema: z.object({
		id: z.string().regex(/^GATE-[A-Z]+-\d{2}$/),
		title: z.string(),
		group: z.enum(['supervision', 'temperature', 'freeze']),
		evidence: z.string(),
		blocks: z.string(),
		status: z.enum(['open', 'passed', 'failed']),
		page: z.string(),
		result: z.string().nullable().default(null),
	}),
});

const decisions = defineCollection({
	loader: glob({
		pattern: 'DEC-*.md',
		base: 'src/data/decisions',
		generateId: ({ data }) => String(data.id),
	}),
	schema: z.object({
		id: z.string().regex(/^DEC-\d{3}$/),
		title: z.string(),
		status: z.enum(['proposed', 'accepted', 'superseded']),
		date,
		revision: z.string(),
		page: z.string(),
		supersedes: z.array(reference('decisions')).default([]),
		requirements: z.array(reference('requirements')).default([]),
		parts: z.array(reference('parts')).default([]),
		gates: z.array(reference('gates')).default([]),
		rejected: z
			.array(z.object({ option: z.string(), reason: z.string(), outcome: z.string().default('rejected') }))
			.default([]),
	}),
});

const status = defineCollection({
	loader: file('src/data/status.yaml'),
	schema: z.object({
		id: z.string(),
		area: z.string(),
		selection: z.string(),
		state: z.enum(['locked', 'risk', 'blocked']),
		note: z.string(),
		page: z.string(),
	}),
});

const sources = defineCollection({
	loader: file('src/data/sources.yaml'),
	schema: z.object({
		id: z.string().regex(/^[SZ]\d+[A-Z]?$/),
		title: z.string(),
		url: z.string().url().optional(),
		verified: date.optional(),
	}),
});

// Firmware pin plan for U401, keyed by net (drawn with the generated mcu-pins.json).
const mcuConfig = defineCollection({
	loader: file('src/data/mcu-config.yaml'),
	schema: z.object({
		function: z.string(),
		group: z.enum(['t1s', 'spi-switch', 'spi-flash', 'i2c', 'adc', 'irq', 'gpio', 'uart', 'debug', 'system']),
		dir: z.enum(['in', 'out', 'io', 'analog', 'od']),
		pull: z.enum(['none', 'up', 'down']),
		edge: z.enum(['rising', 'falling', 'both']).optional(),
		init: z.enum(['low', 'high']).optional(),
		note: z.string().optional(),
	}),
});

export const collections = {
	docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),
	mcuConfig,
	requirements,
	parts,
	gates,
	decisions,
	status,
	sources,
};
