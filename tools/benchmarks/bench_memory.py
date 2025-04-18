import json, time, os, tempfile, subprocess, sys, tracemalloc
def run(lon, lat, label):
    outfile = tempfile.NamedTemporaryFile(delete=False, suffix='.graphml').name
    cmd = [sys.executable, 'tools/export_slice.py', 'slice',
           '--lon', str(lon), '--lat', str(lat),
           '--minutes','60',
           '--outfile', outfile]
    start=time.time()
    subprocess.check_call(cmd)
    elapsed=time.time()-start
    size=os.path.getsize(outfile)/1e6
    tracemalloc.start()
    import networkx as nx
    nx.read_graphml(outfile)
    cur, peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return dict(label=label,size_mb=round(size,1),elapsed_s=round(elapsed,1),peak_ram_mb=round(peak/1e6,1))
def main():
    AOIS={'LA-Contrail':(-92.95,31.14),'IA-Central':(-93.63,41.99),
          'IA-West':(-95.86,41.26),'CA-NTC':(-116.68,35.31)}
    results=[run(lon,lat,label) for label,(lon,lat) in AOIS.items()]
    with open('benchmark_results.json','w') as f: json.dump(results,f,indent=2)
    print(results)
if __name__=='__main__': main()
