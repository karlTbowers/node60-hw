#!/bin/zsh
# pictures.sh [ATTEMPT ...] -- labelled before/after pictures into img/<attempt>/ (before = main);
# with names, only those attempts.
HERE=${0:A:h}; cd $HERE
ONLY=("$@")
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
M=boards/00-main.kicad_pcb
pic(){ $KPY study_picture.py "$@" 2>&1 | grep -E "written|Error|error" ; }
pair(){ # pair ATTEMPT TAG REGION SCALE "TITLE" NETS HI [extra args...]
  local a=$1 tag=$2 reg=$3 sc=$4 title=$5 nets=$6 hi=$7; shift 7
  (( ${#ONLY} )) && [[ ${ONLY[(Ie)$a]} -eq 0 ]] && return
  mkdir -p img/$a
  pic $M img/$a/${tag}_1_before.png --region $reg --scale $sc --title "$a  BEFORE (main): $title" --nets $nets --hi $hi "$@"
  pic boards/$a.kicad_pcb img/$a/${tag}_2_after.png --region $reg --scale $sc --title "$a  AFTER: $title" --nets $nets --hi $hi --moves boards/$a.moves.json "$@"
}
SIG=3V3_MAIN,GND,TMP175_ALERT_L,I2C0_TELEMETRY_SCL,I2C0_TELEMETRY_SDA
pair 01-tmp175-home u203 104,62,128,78 40 "U203 (TMP175), its decap C215 and ALERT pull-up R211" $SIG C215,R211 --layers In3.Cu.PWR --track-layers B.Cu --pins U203
pair 01-tmp175-home east 178,64,244,108 15 "where C215 and R211 stood, and the 3V3 track drawn for them" $SIG,VBAT_PROT C215,R211 --layers In3.Cu.PWR
pair 02-east-feed east 206,64,246,116 22 "3V3 into the east output cell (R807, R801)" 3V3_MAIN,GND,SW_VDD,NTC_SW3,VBAT_PROT R801,R807 --layers In3.Cu.PWR
pair 02-east-feed vias_mid 144,98,164,114 40 "the middle cell's join: a via between two B.Cu tracks" 3V3_MAIN,GND,SW_VDD,NTC_SW2 R701,R707 --layers In3.Cu.PWR --track-layers B.Cu
pair 03a-i2c-pullups-row mcu 184,42,216,72 28 "I2C pull-ups R406, R407 at the MCU" $SIG R406,R407 --layers In3.Cu.PWR --track-layers B.Cu --rats
pair 03a-i2c-pullups-row u203 104,62,128,78 40 "the end of the I2C bus at U203" $SIG R406,R407,R211,C215 --layers In3.Cu.PWR --track-layers B.Cu --pins U203
pair 03a-i2c-pullups-row bus 104,40,216,80 9 "the I2C bus U401 - U202 - U203 and its pull-ups" $SIG R406,R407 --layers In3.Cu.PWR --rats --nolabel
pair 04-irq-pullup link 150,36,214,74 15 "T1S_IRQ_L from U501 pin 22 to U401 ball B3 and its pull-up R508" 3V3_MAIN,GND,T1S_IRQ_L R508 --layers In3.Cu.PWR --rats --track-layers B.Cu
pair 04-irq-pullup mcu 186,50,208,68 40 "U401's south-west corner" 3V3_MAIN,GND,T1S_IRQ_L,BATT_MON,NTC_RSENSE R508 --layers In3.Cu.PWR --track-layers B.Cu --allvias
NTC=3V3_MAIN,GND,NTC_SW1,NTC_SW2,NTC_SW3,SW_VDD
pair 05-ntc-to-mcu cell_west 62,96,96,118 28 "west cell (U601): NTC RT601, pull-up R607, filter C607" $NTC R607,C607,RT601 --layers In3.Cu.PWR,B.Cu --track-layers B.Cu
pair 05-ntc-to-mcu cell_mid 138,96,168,118 28 "middle cell (U701): NTC RT701, pull-up R707, filter C707" $NTC R707,C707,RT701 --layers In3.Cu.PWR,B.Cu --track-layers B.Cu
pair 05-ntc-to-mcu cell_east 212,96,246,118 28 "east cell (U801): NTC RT801, pull-up R807, filter C807" $NTC R807,C807,RT801 --layers In3.Cu.PWR,B.Cu --track-layers B.Cu
pair 05-ntc-to-mcu mcu 186,42,216,72 28 "the NTC pull-ups and filters at the MCU's south side" $NTC R607,C607,R707,C707,R807,C807 --layers In3.Cu.PWR --track-layers B.Cu --rats
pair 05-ntc-to-mcu board 40,30,270,140 7 "the three NTC lines and the 3V3 copper across the board" $NTC R607,C607,R707,C707,R807,C807 --layers In3.Cu.PWR --rats --nolabel
pair 06-phy-strap u501 146,36,168,52 48 "U501's MODE0 strap R513 (pin 23, east edge)" 3V3_MAIN,GND,T1S_MODE0,T1S_MODE1,T1S_IRQ_L,T1S_PHYAD4 R513 --layers In3.Cu.PWR --track-layers B.Cu --allvias --pins U501 --rats
ALL=3V3_MAIN,GND,NTC_SW1,NTC_SW2,NTC_SW3,TMP175_ALERT_L,T1S_IRQ_L,I2C0_TELEMETRY_SCL,I2C0_TELEMETRY_SDA,T1S_MODE0
HI=C215,R211,R406,R407,R508,R607,C607,R707,C707,R807,C807,R513
pair 07a-combined board 40,30,270,140 7 "all six moves: In3 planes, 3V3 tracks and the moved parts' nets" $ALL $HI --layers In3.Cu.PWR --rats --nolabel
pair 07a-combined mcu 184,42,216,72 28 "the MCU's south side with every move in" $ALL $HI --layers In3.Cu.PWR --track-layers B.Cu --rats
pair 07a-combined u203 104,62,128,78 40 "U203 with its decap and the three pull-ups" $ALL $HI --layers In3.Cu.PWR --track-layers B.Cu --pins U203
pair 07a-combined cell_east 206,64,246,118 22 "the east cell and its 3V3 feed" $ALL,SW_VDD $HI --layers In3.Cu.PWR
pair 03b-i2c-pullups-stair mcu 184,42,216,72 28 "I2C pull-ups R406, R407 at the MCU" $SIG R406,R407 --layers In3.Cu.PWR --track-layers B.Cu --rats
pair 03b-i2c-pullups-stair u203 104,62,128,78 40 "the end of the I2C bus at U203" $SIG R406,R407,R211,C215 --layers In3.Cu.PWR --track-layers B.Cu --pins U203
pair 03b-i2c-pullups-stair bus 104,40,216,80 9 "the I2C bus U401 - U202 - U203 and its pull-ups" $SIG R406,R407 --layers In3.Cu.PWR --rats --nolabel
pair 07b-combined board 40,30,270,140 7 "all six moves: In3 planes, 3V3 tracks and the moved parts' nets" $ALL $HI --layers In3.Cu.PWR --rats --nolabel
pair 07b-combined mcu 184,42,216,72 28 "the MCU's south side with every move in" $ALL $HI --layers In3.Cu.PWR --track-layers B.Cu --rats
pair 07b-combined u203 104,62,128,78 40 "U203 with its decap and the three pull-ups" $ALL $HI --layers In3.Cu.PWR --track-layers B.Cu --pins U203
pair 07b-combined cell_east 206,64,246,118 22 "the east cell and its 3V3 feed" $ALL,SW_VDD $HI --layers In3.Cu.PWR
C8=3V3_MAIN,GND,SW_VDD,NTC_SW1,NTC_SW2,NTC_SW3
H8=R601,R701,R801,R607,C607,R707,C707,R807,C807
pair 08-no-3v3-into-cells band 62,94,246,116 8 "the 3V3 track on B.Cu along the power band, and the parts it fed" $C8 $H8 --layers In3.Cu.PWR --track-layers B.Cu --nolabel
pair 08-no-3v3-into-cells west 62,94,100,118 26 "west cell: R601 at the margin's via, SW_VDD runs on to R604 and pin 3" $C8 $H8 --layers In3.Cu.PWR --track-layers B.Cu --rats
pair 08-no-3v3-into-cells mid 138,94,168,118 28 "middle cell: no 3V3 part left; SW_VDD comes in with the cell's signals" $C8 $H8 --layers In3.Cu.PWR --track-layers B.Cu --rats
pair 08-no-3v3-into-cells east 212,94,246,118 26 "east cell: R801 at the margin's via" $C8 $H8 --layers In3.Cu.PWR --track-layers B.Cu --rats
pair 08-no-3v3-into-cells mcu 186,42,216,72 28 "the NTC parts and R701 on the 3V3 plane south of the MCU" $C8 $H8 --layers In3.Cu.PWR --track-layers B.Cu --rats
pair 09-everything board 40,30,270,140 7 "every move: In3 planes, 3V3 tracks and the moved parts' nets" $ALL,SW_VDD $HI,R601,R701,R801 --layers In3.Cu.PWR --rats --nolabel
