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
        def getYResolution(s): return 1080
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
        enabled = details = alert = True
        def isEnabled(s): return s.enabled
        def setEnabled(s, v): s.enabled = v
        def isShowDetails(s): return s.details
        def setShowDetails(s, v): s.details = v
        def isShowAlert(s): return s.alert
        def getPanelX(s): return 5
        def getPanelY(s): return 150
    class G: CapitulationMeter = Opt()
    traces = []
    class Ini:
        reads = 0
        def __init__(s, filename): s.config = W(); s.config.filename = filename
        def isLoaded(s): return True
        def fileExists(s): return True
        def read(s): s.reads += 1
    class Opts:
        ini = Ini(None)
        def getFile(s, id): assert id == "CapitulationMeter"; return s.ini
    mod("BugCore", game=G()); mod("BugOptions", write=lambda: None, getOptions=Opts)
    warns = []
    mod("BugUtil", trace=lambda m: traces.append(m + "\n" + traceback.format_exc()), warn=warns.append)
    added = []
    class Tab:
        def __init__(s, name): s.name = name
        def getName(s): return s.name
        def createMiscellaneousPanel(s, screen, panel): added.append(("original", panel))
        def addSpacer(s, screen, panel, name): pass
        def addLabel(s, screen, panel, name, title): pass
        def addCheckbox(s, screen, panel, name): added.append((name, panel))
    class OptScreen: tabs = [Tab("Other"), Tab("General"), Tab("Last")]
    mod("BugOptionsScreen", getOptionsScreen=lambda: OptScreen)
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
        for l in M.buildLines(r, imp_, 2, 99):
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
    txt = u"\n".join(M.formatReport(r, 2))
    check("power met stays short", (txt.find(u"limit about 593") > 0, txt.find(u"limit:") < 0), (True, True))
    check("size met has no hint", txt.find(u"get either") < 0, True)
    r.bPower = False; r.iMultiplier = 190
    txt = u"\n".join(M.formatReport(r, 2))
    check("limited by average", [txt.find(s) > 0 for s in (u"must drop to about 593", u"limit: average civ", u"neighbour: T2", u"+50% resistance", u"your strength")], [True] * 4 + [False])
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
    r.bPower = False; txt = u"\n".join(M.formatReport(r, 2))
    check("limited by you", [txt.find(s) > 0 for s in (u"limit: your strength", u"limit cut 25%:", u"T2 did more damage", u"average civ")], [True] * 3 + [False])
    S.locked[(1, 2)] = 1; r = rep()[0][0]; check("locked peace", r.blockers, [u"They cannot make peace with T2"])
    S.locked = {}; S.worst = ""; S.succ.pop((2, 1)); del S.war[(1, 2)]; del S.war[(2, 1)]
    # size: both >= 50% -> refuse; one under -> ok
    S.land[1] = 100; S.pop[1] = 75
    check("size hint", u"\n".join(M.formatReport(rep()[0][0], 2)).find(u"of yours (get either below 50%)") > 0, True)
    check("size refuse at 50/50", rep()[0][0].bSize, False); S.pop[1] = 74
    check("size ok one under", rep()[0][0].bSize, True); S.land[1] = 60; S.pop[1] = 40
    S.denial = 5; show("all checks fine, engine refuses"); S.denial = -1
    S.feud = False; show("no Feudalism"); S.feud = True
    S.vassal[1] = 2; show("enemy is a vassal"); del S.vassal[1]
    # several wars: T1 (nothing missing) before T2 (much missing); T3 is T2's vassal
    war(0, 2); war(0, 3); S.vassal[3] = 2; S.talk = True; S.denial = 5
    S.war[(1, 2)] = S.war[(2, 1)] = 1
    r, imp_ = rep()
    full = M.buildLines(r, imp_, 2, 99)
    n1 = [len(M.formatReport(x, 2)) for x in r if x.name == u"T1"][0]
    n2 = [len(M.formatReport(x, 2)) for x in r if x.name == u"T2"][0]
    heads = [l for l in full if l.find(">T") >= 0]
    check("all wars listed, closest first", [l.split(">")[1][:2] for l in heads], [u"T1", u"T2", u"T3"])
    check("all in full", len(full), n1 + n2 + 1)
    check("exact fit", len(M.buildLines(r, imp_, 2, n1 + n2 + 1)), n1 + n2 + 1)
    check("one line short collapses T2", len(M.buildLines(r, imp_, 2, n1 + n2)), n1 + 2)
    check("tiny screen all compact", len(M.buildLines(r, imp_, 2, 3)), 3)
    cut = M.buildLines(r, imp_, 2, 2); check("too many", (len(cut), cut[1].find(u"and 2 more") > 0), (2, True))
    check("never too long", max([len(M.buildLines(r, imp_, 2, k)) - k for k in range(1, 40)]) <= 0, True)
    for k in [(0, 2), (2, 0), (0, 3), (3, 0), (1, 2), (2, 1)]: del S.war[k]
    del S.vassal[3]; S.denial = -1
    # drawing
    M.init(); M.wrapMainInterface()
    check("new settings file reopened", Opts.ini.reads, 1)
    Opts.ini = Ini("x.ini"); M.reopenNewSettings(); check("existing one left alone", Opts.ini.reads, 0)
    check("wrap", CMI().interfaceScreen(), 7)
    for t in OptScreen.tabs: t.createMiscellaneousPanel("scr", t.name)
    check("options only on General tab", added, [("original", "Other"), ("original", "General"),
        ("CapitulationMeter__Enabled", "General"), ("CapitulationMeter__ShowDetails", "General"),
        ("CapitulationMeter__ShowAlert", "General"), ("original", "Last")])
    tabs, OptScreen.tabs = OptScreen.tabs, []
    M.extendOptionsScreen(); check("no General tab only warns", len(warns), 1); OptScreen.tabs = tabs
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
    M.cycleMode(()); tick(); check("compact", (M.getMode(), M.g_iLinesShown), (1, 1))
    M.cycleMode(()); tick(); check("off", (M.getMode(), M.g_iLinesShown), (0, 0))
    M.cycleMode(()); tick(); check("full", (M.getMode(), M.g_iLinesShown > 1), (2, True))
    # settings page: hide the panel, and hide it even during the AI's turn
    M.CapOpt.enabled = False; tick(); check("unchecked hides", M.g_iLinesShown, 0)
    M.CapOpt.enabled = True; tick(); check("checked shows", M.g_iLinesShown > 0, True)
    Player.isTurnActive = lambda s: False
    M.CapOpt.enabled = False; tick(); check("hides on AI turn", M.g_iLinesShown, 0)
    Player.isTurnActive = lambda s: True
    # hidden panel still alerts, unless alerts are off too
    M.g_readyTeams = {}; tick(); check("hidden still alerts", len(msgs), 2)
    M.CapOpt.alert = False; M.g_readyTeams = {}; tick(); check("alerts off", len(msgs), 2)
    M.CapOpt.alert = True; M.CapOpt.enabled = True; tick()
    CMI().interfaceScreen(); check("reset after rebuild", (M.g_bPanelCreated, M.g_iLinesShown), (False, 0))
    S.war = {}; tick(); check("peace hides", M.g_iLinesShown, 0)
    check("broken / traces", (M.g_bBroken, traces), (False, []))
except:
    say("HARNESS ERROR\n" + traceback.format_exc())
OUT.close()
