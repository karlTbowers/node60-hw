// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// Node60 architecture site (DropOut Hardware Handbook, chapter 08).
// Published from main by .github/workflows/docs.yml to https://karltbowers.github.io/node60-hw/
export default defineConfig({
	site: 'https://karltbowers.github.io',
	base: '/node60-hw',
	trailingSlash: 'always',
	integrations: [
		starlight({
			title: 'Node60',
			description:
				'Node60: open-hardware automotive power distribution node. Six protected high-side outputs with current and voltage telemetry over 10BASE-T1S.',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/karlTbowers/node60-hw' }],
			editLink: { baseUrl: 'https://github.com/karlTbowers/node60-hw/edit/main/docs/' },
			lastUpdated: true,
			customCss: ['./src/styles/custom.css'],
			sidebar: [
				{ label: 'Decision overview', link: '/' },
				{ label: 'Purpose & design basis', slug: 'requirements' },
				{ label: 'System architecture', slug: 'system' },
				{
					label: 'Subsystems',
					items: [
						{ label: 'Power entry & rails', slug: 'subsystems/power' },
						{ label: 'Compute, clock & reset', slug: 'subsystems/compute' },
						{ label: 'Watchdog & supervision', slug: 'subsystems/supervision' },
						{ label: '10BASE-T1S', slug: 'subsystems/network' },
						{ label: 'Output stage', slug: 'subsystems/outputs' },
						{ label: 'Temperature sensing', slug: 'subsystems/temperature' },
						{ label: 'Connector & harness', slug: 'subsystems/harness' },
						{ label: 'Firmware & data contract', slug: 'subsystems/firmware' },
						{ label: 'Safety, EMC & thermal', slug: 'subsystems/safety' },
					],
				},
				{ label: 'Decisions', slug: 'decisions' },
				{ label: 'Component baseline', slug: 'components' },
				{ label: 'Schematic interfaces', slug: 'interfaces' },
				{ label: 'Verification gates', slug: 'verification' },
				{ label: 'Source register', slug: 'sources' },
				{ label: 'Revisions', slug: 'revisions' },
			],
		}),
	],
});
