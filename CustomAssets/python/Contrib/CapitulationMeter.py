## CapitulationMeter
##
## Shows, for every AI you are at war with, how close it is to capitulating to you
## and which of the game's conditions are still missing.
##
## The YES/NO verdict is the game's own: it calls CyPlayer.getTradeDenial() for a
## TRADE_SURRENDER item, which is exactly what the diplomacy screen and the AI use.
## The per-condition numbers re-implement CvTeamAI::AI_surrenderTrade() (BTS 3.19)
## because the DLL exposes only the verdict and not the reasons behind it.
##
## Read-only: changes nothing in the game. Disabled in network multiplayer.
##
## Settings are on the General tab of the BUG options screen.
## Alt+Ctrl+V cycles: full details / one line per enemy / hidden.
##
## Copyright (C) 2026 Capitulation Meter contributors
## License: GNU General Public License, version 3 or later. See LICENSE.

from CvPythonExtensions import *
import time
import BugCore
import BugOptions
import BugUtil
import CvMainInterface
import CvScreenEnums
import CvUtil
import DiplomacyUtil

gc = CyGlobalContext()
CapOpt = BugCore.game.CapitulationMeter

MODE_OFF = 0
MODE_COMPACT = 1
MODE_FULL = 2

# CvPlayer::getTradeDenial() passes this to AI_surrenderTrade()
POWER_MULTIPLIER = 140
# CvTeamAI::AI_isLandTarget()
LAND_TARGET_PLOTS = 8
# CvPlayerAI::AI_doPeace(): AI makes contact when its war counter is above this
AI_OFFER_WAR_TURNS = 10

REFRESH_SECONDS = 1.0
LINE_HEIGHT = 17
BOTTOM_HUD_HEIGHT = 180
PANEL = "CapMeterPanel"

GREEN = "80,255,80,255"
YELLOW = "255,255,0,255"
RED = "255,96,96,255"
GREY = "190,190,190,255"

g_bPanelCreated = False
g_iLinesShown = 0
g_drawnKey = None
g_fNextRefresh = 0.0
g_bBroken = False
g_readyTeams = {}
g_borderKey = None
g_borders = None


## ---- Game rules ------------------------------------------------------------

def truncDiv(a, b):
	"""Integer division that truncates toward zero, like C++."""
	q = abs(a) // abs(b)
	if (a < 0) != (b < 0):
		return -q
	return q

def teamPlayers(eTeam):
	players = []
	for i in range(gc.getMAX_PLAYERS()):
		pPlayer = gc.getPlayer(i)
		if pPlayer.isAlive() and pPlayer.getTeam() == eTeam:
			players.append(pPlayer)
	return players

def ownLand(eTeam):
	# CyTeam.getTotalLand() includes vassals; canVassalRevolt() does not
	return sum([p.getTotalLand() for p in teamPlayers(eTeam)])

def ownPopulation(eTeam):
	return sum([p.getTotalPopulation() for p in teamPlayers(eTeam)])


class Borders:
	"""Land borders and city areas, scanned once and reused until land changes hands."""

	def __init__(self):
		self.adjacent = {}      # (owner, neighbor) -> owner's land plots touching neighbor's land
		self.cityAreas = {}     # team -> {areaID: 1}
		self.primaryAreas = {}  # team -> {areaID: 1}
		self.scanPlots()
		self.scanCities()

	def scanPlots(self):
		pMap = CyMap()
		iW = pMap.getGridWidth()
		iH = pMap.getGridHeight()
		bWrapX = pMap.isWrapX()
		bWrapY = pMap.isWrapY()
		owners = []
		for i in range(pMap.numPlots()):
			pPlot = pMap.plotByIndex(i)
			if pPlot.isWater():
				owners.append(-1)
			else:
				owners.append(pPlot.getTeam())
		for y in range(iH):
			for x in range(iW):
				eOwner = owners[y * iW + x]
				if eOwner < 0:
					continue
				touching = {}
				for dy in (-1, 0, 1):
					ny = y + dy
					if ny < 0 or ny >= iH:
						if not bWrapY:
							continue
						ny %= iH
					for dx in (-1, 0, 1):
						nx = x + dx
						if nx < 0 or nx >= iW:
							if not bWrapX:
								continue
							nx %= iW
						eOther = owners[ny * iW + nx]
						if eOther >= 0 and eOther != eOwner:
							touching[eOther] = 1
				for eOther in touching.keys():
					key = (eOwner, eOther)
					self.adjacent[key] = self.adjacent.get(key, 0) + 1

	def scanCities(self):
		for i in range(gc.getMAX_PLAYERS()):
			pPlayer = gc.getPlayer(i)
			if not pPlayer.isAlive():
				continue
			eTeam = pPlayer.getTeam()
			counts = {}
			(pCity, iIter) = pPlayer.firstCity(False)
			while pCity:
				iArea = pCity.plot().getArea()
				counts[iArea] = counts.get(iArea, 0) + 1
				(pCity, iIter) = pPlayer.nextCity(iIter, False)
			primary = self.primaryAreas.setdefault(eTeam, {})
			cities = self.cityAreas.setdefault(eTeam, {})
			for iArea, iCount in counts.items():
				cities[iArea] = 1
				if iCount > 2:
					primary[iArea] = 1
			pCapital = pPlayer.getCapitalCity()
			if pCapital and not pCapital.isNone():
				primary[pCapital.plot().getArea()] = 1

	def isLandTarget(self, eTeam, eTarget):
		"""CvTeamAI::AI_isLandTarget(): eTarget is a land target of eTeam."""
		if self.adjacent.get((eTarget, eTeam), 0) < LAND_TARGET_PLOTS:
			return False
		targetAreas = self.cityAreas.get(eTarget, {})
		for iArea in self.primaryAreas.get(eTeam, {}).keys():
			if iArea in targetAreas:
				return True
		return False

def getBorders():
	global g_borderKey, g_borders
	key = [gc.getGame().getGameTurn()]
	for i in range(gc.getMAX_PLAYERS()):
		pPlayer = gc.getPlayer(i)
		if pPlayer.isAlive():
			key.append((i, pPlayer.getTotalLand(), pPlayer.getNumCities()))
	if g_borders is None or key != g_borderKey:
		g_borders = Borders()
		g_borderKey = key
	return g_borders


class Report:
	"""Everything AI_surrenderTrade() looks at for one enemy team."""

	def __init__(self, eVictim, eMaster, ePlayer):
		self.eVictim = eVictim
		self.eMaster = eMaster
		self.pVictim = gc.getTeam(eVictim)
		self.pMaster = gc.getTeam(eMaster)
		self.name = self.pVictim.getName()
		self.blockers = []
		self.boosts = []
		self.askGame(ePlayer)
		self.checkSuccess()
		self.checkPower()
		self.checkSize()
		self.checkVictory()
		self.checkOtherWars()
		self.iWarTurns = self.pVictim.AI_getAtWarCounter(eMaster)

	def askGame(self, ePlayer):
		eLeader = self.pVictim.getLeaderID()
		pLeader = gc.getPlayer(eLeader)
		item = TradeData()
		item.ItemType = TradeableItems.TRADE_SURRENDER
		item.iData = 0
		self.bCanTrade = pLeader.canTradeItem(ePlayer, item, False)
		self.iDenial = int(pLeader.getTradeDenial(ePlayer, item))
		self.bAgrees = self.bCanTrade and self.iDenial == int(DenialTypes.NO_DENIAL)
		self.bTalks = (gc.getPlayer(ePlayer).canContact(eLeader)
				and DiplomacyUtil.isWillingToTalk(eLeader, ePlayer))

	def checkSuccess(self):
		self.iMySuccess = self.pMaster.AI_getWarSuccess(self.eVictim)
		self.iTheirSuccess = self.pVictim.AI_getWarSuccess(self.eMaster)
		self.iSuccessNeeded = self.iTheirSuccess + 4 * gc.getDefineINT("WAR_SUCCESS_CITY_CAPTURING")
		self.bSuccess = self.iMySuccess >= self.iSuccessNeeded

	def checkPower(self):
		pGame = gc.getGame()
		iModifier = 0
		members = teamPlayers(self.eVictim)
		for pPlayer in members:
			iModifier += gc.getLeaderHeadInfo(pPlayer.getPersonalityType()).getVassalPowerModifier()
		iMultiplier = POWER_MULTIPLIER + truncDiv(iModifier, max(1, len(members)))

		iOwn = self.pVictim.getPower(True)
		iMasterRaw = self.pMaster.getPower(False)
		iAverage = pGame.countTotalCivPower() // max(1, pGame.countCivTeamsAlive())
		iEffective = iOwn * iMultiplier // 100

		iMine = max(10, self.iMySuccess)
		iTheirs = max(10, self.iTheirSuccess)
		iOthersBest = 0
		self.rival = None
		for eTeam in range(gc.getMAX_CIV_TEAMS()):
			if eTeam != self.eMaster and eTeam != self.eVictim:
				pTeam = gc.getTeam(eTeam)
				if pTeam.isAlive() and pTeam.isAtWar(self.eVictim):
					iSuccess = pTeam.AI_getWarSuccess(self.eVictim)
					if iSuccess > iOthersBest:
						iOthersBest = iSuccess
						self.rival = pTeam.getName()
		if iMine < iOthersBest:
			iTheirs += iOthersBest - iMine
		else:
			self.rival = None
		iMaster = 2 * iMasterRaw * iMine // (iMine + iTheirs)

		self.bWorstEnemy = False
		worst = gc.getPlayer(self.pVictim.getLeaderID()).getWorstEnemyName()
		if worst and worst == self.pMaster.getName():
			self.bWorstEnemy = True
			iMaster = iMaster * 3 // 4

		borders = getBorders()
		for eTeam in range(gc.getMAX_CIV_TEAMS()):
			if eTeam == self.eVictim or eTeam == self.eMaster:
				continue
			pTeam = gc.getTeam(eTeam)
			if not pTeam.isAlive() or not borders.isLandTarget(eTeam, self.eVictim):
				continue
			iPower = pTeam.getPower(True)
			bWarMaster = pTeam.isAtWar(self.eMaster)
			bWarVictim = pTeam.isAtWar(self.eVictim)
			bBoost = False
			if iPower > iOwn:
				if bWarMaster and not bWarVictim:
					self.blockers.append(u"%s (strong neighbour) is at war with you but not them" % pTeam.getName())
				iAverage = 2 * iAverage * iPower // max(1, iPower + iOwn)
				bBoost = True
			if not bWarMaster and bWarVictim:
				iAverage = iAverage * (iOwn + iMasterRaw) // max(1, iOwn)
				bBoost = True
			if bBoost:
				self.boosts.append(pTeam.getName())

		# engine refuses when: effective > average, or 3 * effective > 2 * master
		iMasterLimit = 2 * iMaster // 3
		iLimit = min(iAverage, iMasterLimit)
		self.bPower = iEffective <= iLimit
		self.bAverageLimits = iAverage <= iMasterLimit
		self.iPower = iOwn
		# largest raw power whose effective value still fits under the limit
		self.iPowerMax = (100 * (iLimit + 1) - 1) // max(1, iMultiplier)
		self.iMultiplier = iMultiplier

	def checkSize(self):
		self.iLandPercent = 100 * ownLand(self.eVictim) // max(1, ownLand(self.eMaster))
		self.iPopPercent = 100 * ownPopulation(self.eVictim) // max(1, ownPopulation(self.eMaster))
		self.iLandMax = gc.getDefineINT("FREE_VASSAL_LAND_PERCENT")
		self.iPopMax = gc.getDefineINT("FREE_VASSAL_POPULATION_PERCENT")
		self.bSize = (self.iLandMax < 0 or self.iPopMax < 0
				or 100 * ownLand(self.eVictim) < ownLand(self.eMaster) * self.iLandMax
				or 100 * ownPopulation(self.eVictim) < ownPopulation(self.eMaster) * self.iPopMax)

	def checkVictory(self):
		pGame = gc.getGame()
		for i in range(gc.getNumVictoryInfos()):
			iPercent = pGame.getAdjustedPopulationPercent(i)
			if iPercent > 0 and 400 * self.pVictim.getTotalPopulation() > 3 * pGame.getTotalPopulation() * iPercent:
				self.blockers.append(u"They are close to a population victory")
				return
			iPercent = pGame.getAdjustedLandPercent(i)
			if iPercent > 0 and 400 * self.pVictim.getTotalLand() > 3 * CyMap().getLandPlots() * iPercent:
				self.blockers.append(u"They are close to a land victory")
				return

	def checkOtherWars(self):
		# a vassal joins its master's wars and peaces, so those must be possible
		for eTeam in range(gc.getMAX_TEAMS()):
			if eTeam == self.eVictim or eTeam == self.eMaster:
				continue
			pTeam = gc.getTeam(eTeam)
			if not pTeam.isAlive() or pTeam.isAVassal():
				continue
			bWarMaster = pTeam.isAtWar(self.eMaster)
			bWarVictim = pTeam.isAtWar(self.eVictim)
			bLocked = not self.pVictim.canChangeWarPeace(eTeam)
			if bWarMaster and not bWarVictim:
				if bLocked or self.pVictim.isForcePeace(eTeam):
					self.blockers.append(u"They cannot join your war on %s (treaty)" % pTeam.getName())
			elif bWarVictim and not bWarMaster:
				if bLocked:
					self.blockers.append(u"They cannot make peace with %s" % pTeam.getName())

	def missing(self):
		return [b for b in (self.bSuccess, self.bPower, self.bSize) if not b] + self.blockers


def getReports():
	"""Returns a list of Reports, and a list of (name, reason) for enemies that can never be asked."""
	pGame = gc.getGame()
	ePlayer = pGame.getActivePlayer()
	eMaster = pGame.getActiveTeam()
	pMaster = gc.getTeam(eMaster)
	reports = []
	impossible = []
	for eTeam in range(gc.getMAX_CIV_TEAMS()):
		if eTeam == eMaster:
			continue
		pTeam = gc.getTeam(eTeam)
		if (not pTeam.isAlive() or pTeam.isBarbarian() or pTeam.isMinorCiv()
				or pTeam.isHuman() or not pTeam.isAtWar(eMaster)):
			continue
		if pTeam.isAVassal():
			impossible.append((pTeam.getName(), u"is a vassal, beat its master instead"))
		elif pGame.isOption(GameOptionTypes.GAMEOPTION_NO_VASSAL_STATES):
			impossible.append((pTeam.getName(), u"vassal states are off in this game"))
		elif pMaster.isAVassal():
			impossible.append((pTeam.getName(), u"you are a vassal yourself"))
		else:
			reports.append(Report(eTeam, eMaster, ePlayer))
	return reports, impossible


## ---- Text ------------------------------------------------------------------

def colored(text, color):
	return u"<color=%s>%s</color>" % (color, text)

def check(bOkay, text):
	if bOkay:
		return colored(u"  + " + text, GREEN)
	return colored(u"  - " + text, RED)

def formatReport(report, iMode):
	lines = []
	if report.bAgrees and report.bTalks:
		lines.append(colored(u"%s: WILL CAPITULATE, ask now!" % report.name, GREEN))
	elif report.bAgrees:
		lines.append(colored(u"%s: ready, but refuses to talk yet" % report.name, YELLOW))
	elif not report.pMaster.isVassalStateTrading():
		lines.append(colored(u"%s: you need Feudalism (vassal states)" % report.name, RED))
	else:
		iMissing = len(report.missing())
		if iMissing:
			lines.append(colored(u"%s: no (%d missing)" % (report.name, iMissing), RED))
		else:
			lines.append(colored(u"%s: no" % report.name, RED))
	if iMode == MODE_COMPACT:
		return lines

	lines.append(check(report.bSuccess, u"War success %d, need %d (theirs %d)"
			% (report.iMySuccess, report.iSuccessNeeded, report.iTheirSuccess)))
	if report.bAverageLimits:
		rule = u"world average"
	else:
		rule = u"your power"
	lines.append(check(report.bPower, u"Their power %d, max ~%d (by %s)"
			% (report.iPower, report.iPowerMax, rule)))
	if report.iMultiplier != POWER_MULTIPLIER:
		lines.append(colored(u"     leader trait: %+d%% resistance" % (report.iMultiplier - POWER_MULTIPLIER), GREY))
	if not report.bAverageLimits and report.bWorstEnemy:
		lines.append(colored(u"     you are their worst enemy (-25%)", GREY))
	if not report.bAverageLimits and report.rival:
		lines.append(colored(u"     %s did more damage than you" % report.rival, GREY))
	if report.bAverageLimits and report.boosts:
		lines.append(colored(u"     max raised by neighbour: %s" % u", ".join(report.boosts), GREY))
	lines.append(check(report.bSize, u"Land %d%% / pop %d%% of yours (one under %d%%)"
			% (report.iLandPercent, report.iPopPercent, report.iLandMax)))
	for blocker in report.blockers:
		lines.append(check(False, blocker))
	if not report.bTalks:
		lines.append(check(False, u"Refuses to talk"))
	if not report.bAgrees and report.bCanTrade and not report.missing():
		# the game disagrees with the checks above; the game is right
		lines.append(check(False, gc.getDenialInfo(report.iDenial).getDescription()))
	if report.iWarTurns <= AI_OFFER_WAR_TURNS:
		lines.append(colored(u"     war turn %d (AI may offer itself after %d)"
				% (report.iWarTurns, AI_OFFER_WAR_TURNS), GREY))
	return lines

def sortKey(report):
	"""Closest to capitulating first."""
	return (not (report.bAgrees and report.bTalks), not report.bAgrees, len(report.missing()), report.name)

def buildLines(reports, impossible, iMode, iMaxLines):
	"""One block per enemy. Those that do not fit in full are shown as one line."""
	reports = [(sortKey(r), r) for r in reports]
	reports.sort()
	blocks = [formatReport(r, MODE_COMPACT) for (key, r) in reports]
	blocks.extend([[colored(u"%s: %s" % (name, reason), GREY)] for (name, reason) in impossible])
	iFree = iMaxLines - len(blocks)
	if iMode == MODE_FULL:
		for i in range(len(reports)):
			full = formatReport(reports[i][1], MODE_FULL)
			iFree -= len(full) - 1
			if iFree < 0:
				break
			blocks[i] = full
	if len(blocks) > iMaxLines:
		iHidden = len(blocks) - (iMaxLines - 1)
		blocks = blocks[:iMaxLines - 1]
		blocks.append([colored(u"... and %d more" % iHidden, GREY)])
	lines = []
	for block in blocks:
		lines.extend(block)
	return lines

def doAlerts(reports):
	"""On-screen message when an enemy becomes willing to capitulate."""
	global g_readyTeams
	ready = {}
	for report in reports:
		if report.bAgrees and report.bTalks:
			ready[report.eVictim] = 1
			if report.eVictim not in g_readyTeams and CapOpt.isShowAlert():
				CyInterface().addMessage(gc.getGame().getActivePlayer(), True, gc.getEVENT_MESSAGE_TIME(),
						u"%s is willing to capitulate to you!" % report.name, None,
						InterfaceMessageTypes.MESSAGE_TYPE_INFO, None,
						ColorTypes(gc.getInfoTypeForString("COLOR_GREEN")), -1, -1, False, False)
	g_readyTeams = ready


## ---- Drawing ---------------------------------------------------------------

def getScreen():
	return CyGInterfaceScreen("MainInterface", CvScreenEnums.MAIN_INTERFACE)

def labelName(i):
	return "CapMeterText%d" % i

def isVisible():
	eShow = CyInterface().getShowInterface()
	return (eShow != InterfaceVisibility.INTERFACE_HIDE_ALL
			and eShow != InterfaceVisibility.INTERFACE_MINIMAP_ONLY
			and not CyInterface().isCityScreenUp()
			and not CyEngine().isGlobeviewUp())

def maxLines():
	"""How many lines fit between the panel's top edge and the bottom HUD."""
	iHeight = getScreen().getYResolution() - BOTTOM_HUD_HEIGHT - CapOpt.getPanelY() - 10
	return max(3, iHeight // LINE_HEIGHT)

def draw(lines):
	global g_bPanelCreated, g_iLinesShown, g_drawnKey
	iX = CapOpt.getPanelX()
	iY = CapOpt.getPanelY()
	key = (iX, iY, tuple(lines))
	if key == g_drawnKey:
		return
	screen = getScreen()
	for i in range(len(lines), g_iLinesShown):
		screen.hide(labelName(i))
	if lines:
		if not g_bPanelCreated:
			screen.addPanel(PANEL, u"", u"", True, False, 0, 0, 0, 0, PanelStyles.PANEL_STYLE_HUD_HELP)
			screen.setHitTest(PANEL, HitTestTypes.HITTEST_NOHIT)
			g_bPanelCreated = True
		iWidth = 0
		for i in range(len(lines)):
			name = labelName(i)
			screen.setLabel(name, "Background", lines[i], CvUtil.FONT_LEFT_JUSTIFY,
					iX + 8, iY + 5 + i * LINE_HEIGHT, -0.3, FontTypes.SMALL_FONT,
					WidgetTypes.WIDGET_GENERAL, -1, -1)
			screen.setHitTest(name, HitTestTypes.HITTEST_NOHIT)
			screen.show(name)
			iWidth = max(iWidth, CyInterface().determineWidth(lines[i]))
		screen.setPanelSize(PANEL, iX, iY, iWidth + 18, len(lines) * LINE_HEIGHT + 10)
		screen.show(PANEL)
	elif g_bPanelCreated:
		screen.hide(PANEL)
	g_iLinesShown = len(lines)
	g_drawnKey = key

def getMode():
	if not CapOpt.isEnabled():
		return MODE_OFF
	if CapOpt.isShowDetails():
		return MODE_FULL
	return MODE_COMPACT

def update():
	"""Brings the panel up to date."""
	pGame = gc.getGame()
	ePlayer = pGame.getActivePlayer()
	iMode = getMode()
	if ePlayer < 0 or pGame.isNetworkMultiPlayer() or not gc.getPlayer(ePlayer).isAlive():
		draw([])
		return
	bShow = iMode != MODE_OFF and isVisible()
	if not bShow:
		draw([])
	if not gc.getPlayer(ePlayer).isTurnActive():
		return
	if not bShow and not CapOpt.isShowAlert():
		return
	reports, impossible = getReports()
	doAlerts(reports)
	if bShow:
		draw(buildLines(reports, impossible, iMode, maxLines()))


## ---- BUG hooks -------------------------------------------------------------

def onGameUpdate(argsList=None):
	global g_fNextRefresh, g_bBroken
	if g_bBroken:
		return
	fNow = time.clock()
	if fNow < g_fNextRefresh:
		# hide at once when the city screen or globe view opens
		if not g_iLinesShown or isVisible():
			return
	g_fNextRefresh = fNow + REFRESH_SECONDS
	try:
		update()
	except:
		# one error report instead of one per second
		g_bBroken = True
		BugUtil.trace("CapitulationMeter - disabled after an error")

def forceRefresh():
	global g_fNextRefresh
	g_fNextRefresh = 0.0

def resetScreen():
	"""The main interface was rebuilt, so the panel must be created again."""
	global g_bPanelCreated, g_iLinesShown, g_drawnKey
	g_bPanelCreated = False
	g_iLinesShown = 0
	g_drawnKey = None
	forceRefresh()

def onGameLoaded(argsList=None):
	global g_readyTeams, g_borders, g_borderKey, g_bBroken
	g_readyTeams = {}
	g_borders = None
	g_borderKey = None
	g_bBroken = False
	forceRefresh()

def cycleMode(argsList=None):
	"""Shortcut: full -> compact -> off -> full."""
	iMode = getMode()
	if iMode == MODE_FULL:
		CapOpt.setShowDetails(False)
	elif iMode == MODE_COMPACT:
		CapOpt.setEnabled(False)
	else:
		CapOpt.setEnabled(True)
		CapOpt.setShowDetails(True)
	BugOptions.write()
	forceRefresh()

def addOptions(tab, screen, panel):
	"""Adds our checkboxes to a panel of the BUG options screen."""
	tab.addSpacer(screen, panel, "CapitulationMeter")
	tab.addLabel(screen, panel, "CapitulationMeter", "Capitulation Meter:")
	tab.addCheckbox(screen, panel, "CapitulationMeter__Enabled")
	tab.addCheckbox(screen, panel, "CapitulationMeter__ShowDetails")
	tab.addCheckbox(screen, panel, "CapitulationMeter__ShowAlert")

def extendOptionsScreen():
	"""Appends our options to the Misc section of BUG's General tab."""
	import BugOptionsScreen
	for tab in BugOptionsScreen.getOptionsScreen().tabs:
		if tab.getName() == "General" and hasattr(tab, "createMiscellaneousPanel"):
			original = tab.createMiscellaneousPanel
			def createMiscellaneousPanel(screen, panel):
				original(screen, panel)
				try:
					addOptions(tab, screen, panel)
				except:
					BugUtil.trace("CapitulationMeter - cannot add options")
			tab.createMiscellaneousPanel = createMiscellaneousPanel
			return
	BugUtil.warn("CapitulationMeter - no General tab in the options screen")

def reopenNewSettings():
	"""
	BUG never saves changes to a settings file in the session that created it, because
	the ConfigObj it made has no file name. Reading the new file again fixes that.
	"""
	ini = BugOptions.getOptions().getFile("CapitulationMeter")
	if ini.isLoaded() and ini.fileExists() and ini.config.filename is None:
		ini.read()

def init():
	try:
		reopenNewSettings()
	except:
		BugUtil.trace("CapitulationMeter - cannot reopen settings")
	extendOptionsScreen()
	wrapMainInterface()

def wrapMainInterface():
	"""Wraps CvMainInterface.interfaceScreen() to learn when the main screen is rebuilt."""
	cls = CvMainInterface.CvMainInterface
	if hasattr(cls, "capMeterWrapped"):
		return
	original = cls.interfaceScreen
	def interfaceScreen(self, *args):
		result = original(self, *args)
		resetScreen()
		return result
	cls.interfaceScreen = interfaceScreen
	cls.capMeterWrapped = True
