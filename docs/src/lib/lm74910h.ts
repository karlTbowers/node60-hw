// LM74910H-Q1 input protection (U201): the values as built and every figure derived from them.
// The calculations page (src/content/docs/calculations/lm74910h.mdx) prints its numbers from
// here, so a changed part value is edited once, in `P` below.
//
// Sources
//   P   schematic page 2, sheets/power-entry.kicad_sch (reference designators as on the sheet)
//   DS  TI LM749x0-Q1 data sheet SNOSDE6C (December 2022, revised August 2025), LM74910H-Q1 rows
//   FET Infineon IAUTN08S5N012L data sheet rev. 1.0 (2024-02-28)
//   TVS Vishay XLD8A24CA data sheet 87200
// All values in SI base units (V, A, Ω, F, s, C).

/** Parts as built. `tol` is the part's tolerance as a fraction. */
export const P = {
	R201: { v: 0.3e-3, tol: 0.01 }, // RSENSE, BVR-Z-R0003-1.0, 4-terminal
	R202: { v: 10, tol: 0.05 }, // series resistor, HGATE pin to the gates
	R203: { v: 10e3, tol: 0.05 }, // FLT pull-up to 3V3_MAIN
	R204: { v: 107e3, tol: 0.01 }, // ladder: SW to UVLO
	R205: { v: 2e3, tol: 0.01 }, // ladder: UVLO to BATT_MON
	R206: { v: 7.87e3, tol: 0.01 }, // ladder: BATT_MON to OV
	R207: { v: 2.1e3, tol: 0.01 }, // ladder: OV to GND
	R208: { v: 26.7e3, tol: 0.01 }, // R(ILIM)
	R209: { v: 49.9, tol: 0.01 }, // RSET
	R210: { v: 383, tol: 0.01 }, // RISCP
	C202: { v: 10e-9, tol: 0.05 }, // Cdvdt, gates to GND (C0G)
	C209: { v: 1e-6, tol: 0.1 }, // CCAP, CAP to VS
	C210: { v: 10e-9, tol: 0.02 }, // BATT_MON filter (C0G)
	C211: { v: 68e-9, tol: 0.05 }, // CTMR (C0G)
	C212: { v: 10e-9, tol: 0.02 }, // CS+ to CS− filter (C0G)
	C213: { v: 10e-9, tol: 0.02 }, // ISCP deglitch, not fitted
} as const;

/** Capacitance HGATE's FETs charge at start-up, nominal (F). Ceramics lose some under DC bias. */
export const COUT = {
	VBAT_PROT: { C203: 100e-9, C204: 100e-9, C205: 4.7e-6, C301: 1e-6, C601: 100e-9, C602: 1e-6, C701: 100e-9, C702: 1e-6, C801: 100e-9, C802: 1e-6 },
	VBAT_FILT: { C206: 4.7e-6, C207: 47e-6, C303: 100e-9, C304: 4.7e-6, C305: 4.7e-6 },
} as const;

type Lim = { min?: number; typ: number; max?: number };

/** Data sheet constants (DS section 6.5 and 6.6 unless noted). */
export const DS = {
	vAcReg: { min: 3.6e-3, typ: 10.5e-3, max: 13.4e-3 }, // V(AC_REG), forward regulation A−C
	vAcRev: { min: 5e-3, typ: 10.5e-3, max: 16e-3 }, // |V(AC_REV)|, fast reverse comparator
	vAcFwd: { min: 150e-3, typ: 177e-3, max: 200e-3 }, // V(AC_FWD), reverse to forward
	vDgate: { min: 9.2, typ: 11.5, max: 14 }, // DGATE − A, 5 V < VS < 65 V
	vHgate: { min: 10, typ: 11.1, max: 14.5 }, // HGATE − OUT
	iDgateSrc: { typ: 18.5e-3 },
	iDgateSink: { typ: 2.67 },
	tDgateOff: { typ: 0.5e-6, max: 0.95e-6 }, // with 10 nF on DGATE
	iHgate: { min: 39e-6, typ: 55e-6, max: 75e-6 }, // HGATE source current
	iHgateSink: { min: 128e-3, typ: 180e-3 },
	iCap: { min: 1.3e-3, typ: 2.7e-3 }, // charge pump source current, CAP − A = 7 V
	iCapH: 4.2e-3, // "charge pump strength" of the LM74910-Q1 and LM74910H-Q1, DS section 4
	vCapUvlo: { min: 5.4, typ: 6.6, max: 7.9 }, // V(CAP UVLO) rising
	tDrvEn0: 175e-6, // fixed term of equation 1
	vCapOn: 12.2,
	vCapOff: 13.2,
	kIlim: 12, // equation 3's constant, in volts
	vSnsTh: { min: 1.08, typ: 1.22, max: 1.32 }, // OCP comparator threshold at ILIM, rising
	vSnsThFall: { min: 1.02, typ: 1.15, max: 1.25 },
	iScp: { min: 9.3e-6, typ: 10.5e-6, max: 12e-6 }, // ISCP bias current, LM74910H-Q1
	vScp0: { min: 17.86e-3, typ: 20e-3, max: 23e-3 }, // V(SNS_SCP) at RISCP = 0 Ω, LM74910H-Q1
	tScp: { typ: 3e-6, max: 5.5e-6 }, // with CGS = 4.7 nF
	iTmrSrc: { min: 65e-6, typ: 85e-6, max: 97e-6 }, // I(TMR_SRC_CB)
	iTmrSink: { min: 2e-6, typ: 2.7e-6, max: 3.66e-6 }, // LM74910H-Q1
	iTmrEq: 82.3e-6, // equation 4's denominator
	vTmrOc: { min: 1.1, typ: 1.2, max: 1.4 }, // V(TMR_OC)
	vTmrFlt: { min: 1.04, typ: 1.1, max: 1.2 }, // V(TMR_FLT)
	kRetry: 22.7e6, // equation 5, s/F
	retryCycles: 32,
	vUvloR: { min: 0.585, typ: 0.6, max: 0.63 },
	vUvloF: { min: 0.533, typ: 0.55, max: 0.573 },
	vOvR: { min: 0.585, typ: 0.6, max: 0.63 },
	vOvF: { min: 0.533, typ: 0.55, max: 0.573 },
	rSw: { min: 10, typ: 22.5, max: 46 }, // SW disconnect switch
	iOvRule: 1e-6, // OV pin leakage the ladder rule of section 9.2.3.8 assumes
	kImon: 0.9, // equation 7
	imonAcc: [
		{ vs: 10e-3, acc: 0.06 },
		{ vs: 20e-3, acc: 0.03 },
		{ vs: 30e-3, acc: 0.02 },
	], // IMON_ACC, LM74910H-Q1
	vImonMax: 5, // recommended operating maximum at IMON
	rFlt: { min: 9.46, typ: 25, max: 60 }, // FLT pull-down
	iQ: { typ: 675e-6, max: 810e-6 }, // LM74910H-Q1, normal operation
	iSleep: { typ: 5.5e-6, max: 10e-6 },
	iShdn: { typ: 2.5e-6, max: 5e-6 },
	rBypass: 7, // SLEEP-mode bypass switch, typical (section 8.4.2)
	iBypassPeak: 0.1,
	iSleepOc: { min: 0.15, typ: 0.25, max: 0.31 },
	sleepRetryCycles: 64,
	vSleepOvR: { min: 19.3, typ: 21.3, max: 23 },
	vSleepOvF: { min: 18.4, typ: 21, max: 22.2 },
	vSleepHi: { typ: 0.85, max: 1.05 },
	vEnHi: { min: 0.6, typ: 0.8, max: 1.05 },
	vAbsMax: 74, // A, VS, OUT and the other battery pins, LM74910H-Q1
	vCaAbsMax: 88, // C to A, LM74910H-Q1
	vOpMax: 65,
	vRevMax: 65,
	csAbsMax: 0.3, // ISCP, CS+ to CS−
} as const;

/** Q201–Q204, IAUTN08S5N012L, both gates driven together. */
export const FET = {
	n: 2, // FETs per bank
	rds10: { typ: 1.0e-3, max: 1.15e-3 }, // both gates at 10 V, 25 °C
	rds6: { typ: 1.3e-3, max: 1.8e-3 }, // both gates at 6 V
	ciss: { typ: 11.8e-9, max: 15.34e-9 },
	crss: { typ: 91e-12, max: 137e-12 },
	qgs: { typ: 51e-9, max: 66e-9 },
	qg: { typ: 178e-9, max: 231e-9 },
	vth: { min: 2.5, typ: 2.9, max: 3.3 },
	vds: 80,
	vgs: 20,
} as const;

export const TVS = { vwm: 24, vbrMin: 26.7, vbrMax: 29.5, vcMax: 26, ipp: 180 } as const;

/** Operating points used in the worked examples. */
export const OP = {
	iRated: 60, // A, the input's rated current (REQ-PWR-002, DEC-001)
	iBreakerTarget: 75, // A, DEC-001
	iScpTarget: 80, // A, DEC-001
	vBat: 13.5, // V, running 12 V system
	vBatNom: 12,
	vAdc: 3.3, // V, ADC reference (3V3_MAIN)
	adcBits: 12,
	iParked: 52e-6, // A, parked budget (network page)
	vBatMaxRev: 16, // V, highest output voltage in TI's pulse 1 check (section 9.4.2)
	fRipple: 30e3, // Hz, top of the ISO 16750-2 / LV124 E-06 sweep the data sheet uses
} as const;

const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);
const par = (a: number, b: number) => (a * b) / (a + b);

// ── Ideal diode (A, C, DGATE) ────────────────────────────────────────────────────────────────
const rBank = { typ: FET.rds10.typ / FET.n, max: FET.rds10.max / FET.n };
export const diode = {
	rBank,
	iReg: { typR: DS.vAcReg.typ / rBank.typ, maxR: DS.vAcReg.typ / rBank.max },
	vDrop: { typ: OP.iRated * rBank.typ, max: OP.iRated * rBank.max },
	pBank: { typ: OP.iRated ** 2 * rBank.typ, max: OP.iRated ** 2 * rBank.max },
	iRevTrip: { typ: DS.vAcRev.typ / rBank.typ, max: DS.vAcRev.max / rBank.typ },
	gateLoad: { typ: FET.n * FET.ciss.typ, max: FET.n * FET.ciss.max },
	qgsBank: { typ: FET.n * FET.qgs.typ, max: FET.n * FET.qgs.max },
	qgsMaxAtRipple: DS.iCap.min / OP.fRipple,
	fRectMax: { typ: DS.iCap.min / (FET.n * FET.qgs.typ), min: DS.iCap.min / (FET.n * FET.qgs.max) },
	vCaPulse1: TVS.vcMax + OP.vBatMaxRev,
};

// ── Charge pump (CAP) ────────────────────────────────────────────────────────────────────────
const cissAll = { typ: 2 * FET.n * FET.ciss.typ, max: 2 * FET.n * FET.ciss.max };
export const pump = {
	cissAll,
	cMin: { typ: 10 * cissAll.typ, max: 10 * cissAll.max },
	tChargeEq: (P.C209.v * DS.vCapUvlo.typ) / DS.iCap.typ,
	tDrvEn: DS.tDrvEn0 + (P.C209.v * DS.vCapUvlo.typ) / DS.iCap.typ,
	tDrvEnH: DS.tDrvEn0 + (P.C209.v * DS.vCapUvlo.typ) / DS.iCapH,
	tDrvEn100n: DS.tDrvEn0 + (100e-9 * DS.vCapUvlo.typ) / DS.iCap.typ,
};

// ── Load disconnect and inrush (HGATE, OUT) ──────────────────────────────────────────────────
const cProt = sum(COUT.VBAT_PROT);
const cFilt = sum(COUT.VBAT_FILT);
const cOut = cProt + cFilt;
const slew = { min: DS.iHgate.min / P.C202.v, typ: DS.iHgate.typ / P.C202.v, max: DS.iHgate.max / P.C202.v };
const iInrush = { typ: (cOut * DS.iHgate.typ) / P.C202.v, max: (cOut * DS.iHgate.max) / P.C202.v };
export const hgate = {
	cProt,
	cFilt,
	cOut,
	slew, // V/s
	iInrush,
	tInrush: (OP.vBat * cOut) / iInrush.typ,
	eInrush: 0.5 * cOut * OP.vBat ** 2,
	pPeak: OP.vBat * iInrush.typ,
	crssBank: FET.n * FET.crss.typ,
	// charge to remove at a turn-off from 13.5 V: both gates, and C202 from OUT + drive down to 0 V
	qGates: FET.n * FET.qg.typ,
	qCdvdt: P.C202.v * (OP.vBat + DS.vHgate.typ),
};

// ── Current sense front end (CS+, CS−, RSET) ─────────────────────────────────────────────────
export const sense = {
	vRated: OP.iRated * P.R201.v,
	pRated: OP.iRated ** 2 * P.R201.v,
	tauCs: P.R209.v * P.C212.v,
	fcCs: 1 / (2 * Math.PI * P.R209.v * P.C212.v),
	iAbsMax: DS.csAbsMax / P.R201.v,
};

// ── Circuit breaker (ILIM, TMR) ──────────────────────────────────────────────────────────────
const iLim = (DS.kIlim * P.R209.v) / (P.R201.v * P.R208.v);
const tOc = (DS.vTmrOc.typ * P.C211.v) / DS.iTmrEq;
const tFlt = (DS.vTmrFlt.typ * P.C211.v) / DS.iTmrEq;
const tRetry = DS.kRetry * P.C211.v;
export const breaker = {
	rIlimIdeal: (DS.kIlim * P.R209.v) / (P.R201.v * OP.iBreakerTarget),
	iLim,
	vSense: iLim * P.R201.v,
	pShunt: iLim ** 2 * P.R201.v,
	margin: iLim / OP.iRated - 1,
	// the equation's 12 V read as a 1.2 V threshold at ILIM on a tenth of VSENSE / RSET
	vIlimEq: DS.kIlim / 10,
	iLimMin: (iLim * DS.vSnsTh.min) / (DS.kIlim / 10),
	iLimTyp: (iLim * DS.vSnsTh.typ) / (DS.kIlim / 10),
	iLimMax: (iLim * DS.vSnsTh.max) / (DS.kIlim / 10),
	tOc,
	tFlt,
	tWarn: tOc - tFlt,
	tOcMin: (DS.vTmrOc.min * P.C211.v * (1 - P.C211.tol)) / (DS.iTmrSrc.max - DS.iTmrSink.typ),
	tOcMax: (DS.vTmrOc.max * P.C211.v * (1 + P.C211.tol)) / (DS.iTmrSrc.min - DS.iTmrSink.typ),
	tRetry,
	tRetry10n: DS.kRetry * 10e-9,
	duty: tOc / (tOc + tRetry),
	cTmrFor1ms: (1e-3 * DS.iTmrEq) / DS.vTmrOc.typ,
};

// ── Short-circuit protection (ISCP) ──────────────────────────────────────────────────────────
const vScp = DS.iScp.typ * P.R210.v + DS.vScp0.typ;
const vScpMin = DS.iScp.min * P.R210.v + DS.vScp0.min;
const vScpMax = DS.iScp.max * P.R210.v + DS.vScp0.max;
export const scp = {
	rIscpIdeal: (OP.iScpTarget * P.R201.v - DS.vScp0.typ) / DS.iScp.typ,
	vShift: DS.iScp.typ * P.R210.v,
	vScp,
	iScp: vScp / P.R201.v,
	vScpMin,
	vScpMax,
	iScpMin: vScpMin / P.R201.v,
	iScpMax: vScpMax / P.R201.v,
	// the default threshold, ISCP tied straight to the shunt
	iDefault: { min: DS.vScp0.min / P.R201.v, typ: DS.vScp0.typ / P.R201.v, max: DS.vScp0.max / P.R201.v },
	tauDeglitch: P.R210.v * P.C213.v,
};

// ── UVLO, OV and BATT_MON ladder (SW, UVLO, OV) ──────────────────────────────────────────────
const rTot = P.R204.v + P.R205.v + P.R206.v + P.R207.v;
const rUv = P.R205.v + P.R206.v + P.R207.v; // below the UVLO tap
const rMon = P.R206.v + P.R207.v; // below the BATT_MON tap
const rOv = P.R207.v; // below the OV tap
const tolRatio = (rBelow: number) => 2 * P.R204.tol * (1 - rBelow / rTot);
const rTh = par(rTot - rMon, rMon);
const tau = rTh * P.C210.v;
const kMon = rMon / rTot;
const lsb = OP.vAdc / 2 ** OP.adcBits;
export const ladder = {
	rTot,
	rUv,
	rMon,
	rOv,
	uvFall: (DS.vUvloF.typ * rTot) / rUv,
	uvRise: (DS.vUvloR.typ * rTot) / rUv,
	uvFallMin: ((DS.vUvloF.min * rTot) / rUv) * (1 - tolRatio(rUv)),
	uvFallMax: ((DS.vUvloF.max * rTot) / rUv) * (1 + tolRatio(rUv)),
	ovRise: (DS.vOvR.typ * rTot) / rOv,
	ovFall: (DS.vOvF.typ * rTot) / rOv,
	ovRiseMin: ((DS.vOvR.min * rTot) / rOv) * (1 - tolRatio(rOv)),
	ovRiseMax: ((DS.vOvR.max * rTot) / rOv) * (1 + tolRatio(rOv)),
	tolUv: tolRatio(rUv),
	tolOv: tolRatio(rOv),
	iLadder12: OP.vBatNom / rTot,
	iLadder: OP.vBat / rTot,
	rRule: OP.vBatNom / (100 * DS.iOvRule),
	rSwErr: DS.rSw.max / rTot,
	kMon,
	ratio: 1 / kMon,
	vMonBat: OP.vBat * kMon,
	vMonOv: ((DS.vOvR.typ * rTot) / rOv) * kMon,
	vFullScale: OP.vAdc / kMon,
	lsb,
	lsbBat: lsb / kMon,
	rTh,
	tau,
	fc: 1 / (2 * Math.PI * tau),
	// R204 at the OV cut-off
	vR204: (((DS.vOvR.typ * rTot) / rOv) * P.R204.v) / rTot,
	pR204: (((DS.vOvR.typ * rTot) / rOv) / rTot) ** 2 * P.R204.v,
	// C210 also slows the UVLO and OV pins: a step from 13.5 V
	uvPinDirect: P.R205.v / (rTot - rMon), // share of a step that reaches UVLO unfiltered
	tUvDip: tau * Math.log((OP.vBat * kMon) / ((DS.vUvloF.typ * (rTot - rMon)) / P.R204.v)),
	ovStepTo: 40,
	tOvStep: tau * Math.log((40 - OP.vBat) / (40 - (DS.vOvR.typ * rTot) / rOv)),
};

// ── SLEEP mode and FLT ───────────────────────────────────────────────────────────────────────
export const sleep = {
	vDropParked: OP.iParked * DS.rBypass,
	vDropPeak: DS.iBypassPeak * DS.rBypass,
	iChargeStart: OP.vBat / DS.rBypass,
	tRetry64: (DS.sleepRetryCycles / DS.retryCycles) * tRetry,
};
export const flt = {
	iLow: OP.vAdc / (P.R203.v + DS.rFlt.typ),
	vLowMax: (OP.vAdc * DS.rFlt.max) / (P.R203.v + DS.rFlt.max),
};

// ── IMON, if it were fitted ──────────────────────────────────────────────────────────────────
// Full scale: the top of the fast trip's window reads 3.0 V, inside the 3.3 V ADC range.
const imonTarget = { v: 3.0, vs: vScpMax };
const rImonIdeal = (imonTarget.v * P.R209.v) / (DS.kImon * imonTarget.vs);
const rImon = 6.04e3; // nearest E96 value
const gImon = (DS.kImon * P.R201.v * rImon) / P.R209.v; // V per A
export const imon = {
	target: imonTarget,
	rImonIdeal,
	rImon,
	gain: gImon,
	vAt: (i: number) => gImon * i,
	points: [10, 30, OP.iRated, iLim, scp.iScp, scp.iScpMax].map((i) => ({ i, vs: i * P.R201.v, v: gImon * i })),
	note: (i: number) =>
		i === OP.iRated ? ' (rated)' : i === iLim ? ' (breaker)' : i === scp.iScp ? ' (fast trip, typical)' : i === scp.iScpMax ? ' (fast trip, maximum)' : '',
	iPerCount: lsb / gImon,
	iFullScale: OP.vAdc / gImon,
	iAtAcc: DS.imonAcc.map((a) => ({ ...a, i: a.vs / P.R201.v })),
	cFilter: 10e-9,
	tau: rImon * 10e-9,
	vAtShort: (DS.kImon * DS.csAbsMax * rImon) / P.R209.v,
};

// ── Formatting ───────────────────────────────────────────────────────────────────────────────
/** Round to `sig` significant figures and drop trailing zeros. */
export function sig(x: number, n = 3): string {
	if (x === 0) return '0';
	const d = Math.max(0, n - 1 - Math.floor(Math.log10(Math.abs(x))));
	return String(Number(x.toFixed(d)));
}
/** Fixed decimals. */
export const fix = (x: number, d = 2) => x.toFixed(d);

const PREFIX: [number, string, string][] = [
	[1e6, 'M', 'M'],
	[1e3, 'k', 'k'],
	[1, '', ''],
	[1e-3, 'm', 'm'],
	[1e-6, 'µ', '\\mu '],
	[1e-9, 'n', 'n'],
	[1e-12, 'p', 'p'],
];
const TEX_UNIT: Record<string, string> = { Ω: '\\Omega ', '°C': '^\\circ C' };

function scale(x: number, prefix?: string): [number, string, string] {
	const a = Math.abs(x);
	const p =
		prefix === undefined
			? (PREFIX.find(([f]) => a >= f * 0.9995) ?? PREFIX[PREFIX.length - 1])
			: PREFIX.find(([, q]) => q === prefix)!;
	return [x / p[0], p[1], p[2]];
}
/** A value with an SI prefix as text: si(0.0003, 'Ω', 3, 'm') = "0.3 mΩ". `prefix` forces one. */
export function si(x: number, unit: string, n = 3, prefix?: string): string {
	const [v, p] = scale(x, prefix);
	return `${sig(v, n)} ${p}${unit}`;
}
/** The same for KaTeX: tex(0.0003, 'Ω', 3, 'm') = "0.3\,\mathrm{m\Omega }". */
export function tex(x: number, unit: string, n = 3, prefix?: string): string {
	const [v, , p] = scale(x, prefix);
	return `${sig(v, n)}\\,\\mathrm{${p}${TEX_UNIT[unit] ?? unit}}`;
}
/** A range as text in the prefix of its upper end: range(0.0214, 0.0276, 'V') = "21.4–27.6 mV". */
export function range(lo: number, hi: number, unit: string, n = 3, prefix?: string): string {
	const [, p] = scale(hi, prefix);
	const f = PREFIX.find(([, q]) => q === p)![0];
	return `${sig(lo / f, n)}–${sig(hi / f, n)} ${p}${unit}`;
}
/** Percent with one decimal by default. */
export const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)} %`;
