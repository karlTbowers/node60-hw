import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
n0 = len(b.GetTracks())
ok = pcbnew.ImportSpecctraSES(b, sys.argv[2])
print("import", ok, "tracks", n0, "->", len(b.GetTracks()))
b.Save(sys.argv[3])
