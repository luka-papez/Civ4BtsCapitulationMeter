import sys, types, traceback
OUT = open(OUTPATH, "w")
def say(s):
    if isinstance(s, unicode): s = s.encode("ascii", "replace")
    OUT.write(str(s) + "\n"); OUT.flush()
try:
    def mod(name, **kw):
        m = types.ModuleType(name); m.__dict__.update(kw); sys.modules[name] = m; return m
    class Any(object):
        def __getattr__(self, n): return n
    class W: pass
    S = W()
    # world: teams 0 human, 1 victim, 2 neighbour, 3 vassal-of-0, 4 barb
    S.power = [1000, 400, 900, 100, 0]
    S.land = [200, 60, 150, 20, 0]; S.pop = [150, 40, 100, 10, 0]
    S.alive = [1, 1, 1, 1, 1]
    S.war = {}
    S.succ = {}
    S.vassal = {}
    S.human = {0: 1}
    S.talk = True; S.feud = True; S.vis = True; S.turn = 10; S.mod = [0, 0, 0, 0, 0]; S.worst = ""
    S.denial = -1
    S.force = {}; S.locked = {}
    S.warcount = 5
    def war(a, b): S.war[(a, b)] = 1; S.war[(b, a)] = 1
    # 12x8 map, columns: team0 x0-3, team1 x4-7, team2 x8-11
    GW, GH = 12, 8
    def owner(i):
        x = i % GW
        if x < 4: return 0
        if x < 8: return 1
        return 2
    class Plot:
        def __init__(s, i): s.i = i
        def isWater(s): return False
        def getTeam(s): return owner(s.i)
        def getArea(s): return 1
    class Map:
        def getGridWidth(s): return GW
        def getGridHeight(s): return GH
        def isWrapX(s): return False
        def isWrapY(s): return False
        def numPlots(s): return GW * GH
        def plotByIndex(s, i): return Plot(i)
        def getLandPlots(s): return 1000
    class City:
        def plot(s): return Plot(0)
        def isNone(s): return False
    class Player:
        def __init__(s, i): s.i = i
        def getID(s): return s.i
        def isAlive(s): return S.alive[s.i]
        def getTeam(s): return s.i
        def getTotalLand(s): return S.land[s.i]
        def getTotalPopulation(s): return S.pop[s.i]
        def getNumCities(s): return 1
        def firstCity(s, r): return (City(), 0)
        def nextCity(s, it, r): return (None, 0)
        def getCapitalCity(s): return City()
        def getPersonalityType(s): return s.i
        def getWorstEnemyName(s): return S.worst
        def canContact(s, o): return True
        def isTurnActive(s): return True
        def canTradeItem(s, o, item, b): assert item.ItemType == "TRADE_SURRENDER"; return S.feud
        def getTradeDenial(s, o, item): return S.denial
    class Team:
        def __init__(s, i): s.i = i
        def getName(s): return u"T%d" % s.i
        def isAlive(s): return S.alive[s.i]
        def isBarbarian(s): return s.i == 4
        def isMinorCiv(s): return False
        def isHuman(s): return s.i in S.human
        def isAtWar(s, o): return (s.i, o) in S.war
        def isAVassal(s): return s.i in S.vassal
        def getLeaderID(s): return s.i
        def AI_getWarSuccess(s, o): return S.succ.get((s.i, o), 0)
        def AI_getAtWarCounter(s, o): return S.warcount
        def getPower(s, b):
            p = S.power[s.i]
            if b:
                for v, m in S.vassal.items():
                    if m == s.i: p += S.power[v]
            return p
        def getTotalPopulation(s): return S.pop[s.i]
        def getTotalLand(s): return S.land[s.i]
        def canChangeWarPeace(s, o): return (s.i, o) not in S.locked
        def isForcePeace(s, o): return (s.i, o) in S.force
        def isVassalStateTrading(s): return S.feud
    class Leader:
        def __init__(s, i): s.i = i
        def getVassalPowerModifier(s): return S.mod[s.i]
    class Game:
        def getGameTurn(s): return S.turn
        def getActivePlayer(s): return 0
        def getActiveTeam(s): return 0
        def countTotalCivPower(s): return sum(S.power[:4])
        def countCivTeamsAlive(s): return sum(S.alive[:4])
        def isNetworkMultiPlayer(s): return False
        def isOption(s, o): return False
        def getAdjustedPopulationPercent(s, i): return 0
        def getAdjustedLandPercent(s, i): return 60
        def getTotalPopulation(s): return 300
    class Info:
        def getDescription(s): return u"ENGINE REASON"
    class GC:
        def getGame(s): return Game()
        def getTeam(s, i): return Team(i)
        def getPlayer(s, i): return Player(i)
        def getMAX_PLAYERS(s): return 5
        def getMAX_TEAMS(s): return 5
        def getMAX_CIV_TEAMS(s): return 4
        def getLeaderHeadInfo(s, i): return Leader(i)
        def getDefineINT(s, n): return {"WAR_SUCCESS_CITY_CAPTURING": 10, "FREE_VASSAL_LAND_PERCENT": 50, "FREE_VASSAL_POPULATION_PERCENT": 50}[n]
        def getNumVictoryInfos(s): return 1
        def getDenialInfo(s, i): return Info()
        def getEVENT_MESSAGE_TIME(s): return 10
        def getInfoTypeForString(s, n): return 1
    msgs = []
    class Iface:
        def getShowInterface(s): return "INTERFACE_SHOW"
        def isCityScreenUp(s): return not S.vis
        def determineWidth(s, t): return 7 * len(t)
        def addMessage(s, *a): assert len(a) == 12; msgs.append(a[3])
    class Eng:
        def isGlobeviewUp(s): return False
    calls = []
    class Screen:
        def __getattr__(s, n):
            def f(*a): calls.append((n, a))
            return f
    class TD: pass
    class Denial: NO_DENIAL = -1
    a = Any()
    mod("CvPythonExtensions", CyGlobalContext=GC, CyMap=Map, CyInterface=Iface, CyEngine=Eng, TradeData=TD,
        TradeableItems=a, DenialTypes=Denial, GameOptionTypes=a, InterfaceMessageTypes=a, ColorTypes=lambda x: x,
        InterfaceVisibility=a, CyGInterfaceScreen=lambda *x: Screen(), PanelStyles=a, HitTestTypes=a, FontTypes=a, WidgetTypes=a)
    class Opt:
        mode = 2
        def getMode(s): return s.mode
        def setMode(s, v): s.mode = v
        def isShowAlert(s): return True
        def getPanelX(s): return 5
        def getPanelY(s): return 150
    class G: CapitulationMeter = Opt()
    traces = []
    mod("BugCore", game=G()); mod("BugOptions", write=lambda: None)
    mod("BugUtil", trace=lambda m: traces.append(m + "\n" + traceback.format_exc()))
    class CMI:
        def interfaceScreen(s): return 7
    mod("CvMainInterface", CvMainInterface=CMI); mod("CvScreenEnums", MAIN_INTERFACE=0); mod("CvUtil", FONT_LEFT_JUSTIFY=0)
    mod("DiplomacyUtil", isWillingToTalk=lambda x, y: S.talk)
    sys.path.insert(0, MODDIR)
    sys.dont_write_bytecode = True
    import imp
    src = open(MODDIR + "/CapitulationMeter.py", "U").read()
    M = types.ModuleType("CapitulationMeter"); sys.modules["CapitulationMeter"] = M
    exec compile(src, "CapitulationMeter.py", "exec") in M.__dict__
    say("python " + sys.version.split()[0] + " compiled OK")
    def check(label, got, want):
        if got == want: say("PASS %s = %r" % (label, got))
        else: say("FAIL %s got %r want %r" % (label, got, want))
    def rep():
        return M.getReports()
    def show(title):
        r, imp_ = rep()
        say("--- " + title)
        for l in M.buildLines(r, imp_, 2):
            say("   " + l)
        return r
    S.succ = {(0, 1): 50, (1, 0): 12}; S.warcount = 5
    war(0, 1); war(0, 4)
    # avg = 2400/4 = 600; neighbour T2 (900>400) borders victim (8 plots): 2*600*900/1300 = 830
    # master = 2*1000*50/62 = 1612 -> limit 2*1612//3 = 1074; so limit 830 by average; eff = 400*140//100 = 560
    r = show("base: success 50 of 52 needed")[0]
    check("success", (r.iMySuccess, r.iSuccessNeeded, r.bSuccess), (50, 52, False))
    check("power", (r.bPower, r.bAverageLimits, r.iPowerMax), (True, True, (100 * 831 - 1) // 140))
    check("boosts", r.boosts, [u"T2"])
    check("size", (r.iLandPercent, r.iPopPercent, r.bSize), (30, 26, True))
    S.succ[(0, 1)] = 52
    check("success boundary", rep()[0][0].bSuccess, True)
    check("land target", (M.getBorders().isLandTarget(2, 1), M.getBorders().isLandTarget(3, 1), M.getBorders().isLandTarget(2, 0)), (True, False, False))
    # exact boundary of power max: at iPowerMax allowed, +1 refused (limit held fixed)
    ok = True
    for mult in (120, 130, 140, 150, 160, 190):
        for limit in range(1, 900):
            m = (100 * (limit + 1) - 1) // mult
            if not (m * mult // 100 <= limit < (m + 1) * mult // 100): ok = False
    check("iPowerMax boundary", ok, True)
    check("truncDiv", (M.truncDiv(-5, 2), M.truncDiv(5, 2), M.truncDiv(-20, 1)), (-2, 2, -20))
    S.mod[1] = -20
    check("gentle leader mult", rep()[0][0].iMultiplier, 120); S.mod[1] = 50
    r = show("Genghis +50")[0]; check("tough leader mult", r.iMultiplier, 190); S.mod[1] = 0
    # strong neighbour at war with us only -> blocked
    war(0, 2)
    r = show("neighbour T2 also at war with us"); check("blocker", len(r[0].blockers), 1)
    del S.war[(0, 2)]; del S.war[(2, 0)]
    # neighbour fights victim too -> avg boost: 830*(400+1000)//400 = 2905; master limits (2*(2*1000*52//64=1625)//3=1083)
    war(1, 2)
    r = rep()[0][0]; check("shared war", (r.bAverageLimits, r.bPower, r.iPowerMax), (False, True, (100 * 1084 - 1) // 140))
    # T2 did more damage: theirs = 12 + (90-52) = 50 ; master = 2000*52//102 = 1019
    S.succ[(2, 1)] = 90; S.worst = u"T0"
    r = show("rival did more + worst enemy")[0]
    check("rival", (r.rival, r.iPowerMax), (u"T2", (100 * ((2 * (1019 * 3 // 4) // 3) + 1) - 1) // 140))
    S.locked[(1, 2)] = 1; r = rep()[0][0]; check("locked peace", r.blockers, [u"They cannot make peace with T2"])
    S.locked = {}; S.worst = ""; S.succ.pop((2, 1)); del S.war[(1, 2)]; del S.war[(2, 1)]
    # size: both >= 50% -> refuse; one under -> ok
    S.land[1] = 100; S.pop[1] = 75
    check("size refuse at 50/50", rep()[0][0].bSize, False); S.pop[1] = 74
    check("size ok one under", rep()[0][0].bSize, True); S.land[1] = 60; S.pop[1] = 40
    S.denial = 5; show("all checks fine, engine refuses"); S.denial = -1
    S.feud = False; show("no Feudalism"); S.feud = True
    S.vassal[1] = 2; show("enemy is a vassal"); del S.vassal[1]
    # drawing
    M.init(); M.init()
    check("wrap", CMI().interfaceScreen(), 7)
    S.talk = False
    def tick():
        M.forceRefresh(); M.onGameUpdate(())
    tick(); check("no alert while not talking", msgs, [])
    check("drawn", M.g_iLinesShown > 0, True)
    S.talk = True
    tick(); tick(); check("alert once", msgs, [u"T1 is willing to capitulate to you!"])
    n = len(calls); tick(); check("no redraw when unchanged", len(calls), n)
    S.vis = False; M.onGameUpdate(()); check("hidden in city screen", M.g_iLinesShown, 0)
    S.vis = True; tick(); check("shown again", M.g_iLinesShown > 0, True)
    M.cycleMode(()); tick(); check("compact", (M.CapOpt.mode, M.g_iLinesShown), (1, 1))
    M.cycleMode(()); tick(); check("off", (M.CapOpt.mode, M.g_iLinesShown), (0, 0))
    M.cycleMode(()); tick(); check("full", M.CapOpt.mode, 2)
    CMI().interfaceScreen(); check("reset after rebuild", (M.g_bPanelCreated, M.g_iLinesShown), (False, 0))
    S.war = {}; tick(); check("peace hides", M.g_iLinesShown, 0)
    check("broken / traces", (M.g_bBroken, traces), (False, []))
except:
    say("HARNESS ERROR\n" + traceback.format_exc())
OUT.close()
