#!/usr/bin/env julia
include(joinpath(@__DIR__, "MCMLS.jl"))
using .MCMLS, TOML, Statistics, Printf, SHA, DelimitedFiles
using Base.Threads: @threads, nthreads
const ROOT = normpath(joinpath(@__DIR__, ".."))
const CFG = TOML.parsefile(joinpath(ROOT, "config/paper.toml"))
const SCENES = ["canonical", "ob_complete", "ob_half", "rx2_competitive", "rx2_half"]
const METHODS = ["monc", "mls_lb", "ams_mod"]
const STUDIES = ["main", "cdf", "uniform-scan", "adaptive-scan"]
const FIELDS = ["scene", "distance_R", "algorithm", "parameter", "experiment", "inner_repeats", "accepted_run", "relative_l2", "relative_mse", "wall_seconds", "q_mean_final", "q_ref_final", "iteration_caps", "total_steps", "propagation_steps", "replay_steps", "clones", "inner_zero_hit_rate"]

function options(args)
    opts = Dict{String,String}(); i = 1
    valued = ["study", "scenes", "methods", "distances", "parameters", "experiments", "repeats", "steps", "output-root", "jobs", "worker"]
    while i <= length(args)
        key = replace(args[i], r"^--" => "")
        startswith(args[i], "--") || error("Expected --option, got $(args[i])")
        haskey(opts, key) && error("Duplicate --$key")
        if key in ["help", "dry-run"]
            opts[key] = "true"
        else
            key in valued || error("Unknown --$key")
            i < length(args) || error("Missing value after --$key")
            i += 1; opts[key] = args[i]
        end
        i += 1
    end
    opts
end
function readcsv(path)
    lines = readlines(path); head = split(first(lines), ',')
    [Dict(String.(head) .=> String.(split(line, ','; keepempty=true))) for line in lines[2:end] if !isempty(line)]
end
cell(x) = x isa AbstractFloat ? (isfinite(x) ? @sprintf("%.17g", x) : "") : string(x)
function writecsv(path, head, rows)
    mkpath(dirname(path))
    open(path, "w") do f
        println(f, join(head, ','))
        for r in rows; println(f, join(cell.(r), ',')); end
    end
end
function selected(opts, key, defaults)
    value = get(opts, key, "all")
    result = value == "all" ? defaults : String.(split(value, ','))
    length(unique(result)) == length(result) || error("Duplicate --$key")
    all(in(defaults), result) || error("Invalid --$key; choices: $(join(defaults, ','))")
    result
end
function dataset(scene, study)
    joinpath(scene, study == "uniform-scan" ? "scans/uniform" : study == "adaptive-scan" ? "scans/adaptive" : study)
end
function plan(opts)
    studies = selected(opts, "study", STUDIES)
    scenes = selected(opts, "scenes", SCENES); methods = selected(opts, "methods", METHODS)
    ds = get(opts, "distances", "all") == "all" ? nothing : parse.(Int, split(opts["distances"], ','))
    ps = get(opts, "parameters", "all") == "all" ? nothing : parse.(Int, split(opts["parameters"], ','))
    ds === nothing || (!isempty(ds) && all(in([5,8,13,21,34]),ds)) || error("Invalid distances")
    jobs = NamedTuple[]
    for study in studies, scene in scenes
        study != "main" && scene != "canonical" && continue
        scan = endswith(study, "-scan")
        sc = scan ? CFG[study == "uniform-scan" ? "uniform_scan" : "adaptive_scan"] : nothing
        parameters = scan ? Int.(sc["parameters"]) : [0]
        scan && ps !== nothing && (parameters = intersect(parameters, ps))
        distances = scan ? Int.(sc["distances"]) : [5,8,13,21,34]
        ds !== nothing && (distances = intersect(distances, ds))
        algs = scan ? [study == "uniform-scan" ? "mls_lb" : "ams_mod"] : METHODS
        algs = intersect(algs, methods)
        limit = scan ? sc["experiments"] : study == "cdf" ? 1 : 50
        batches = parse(Int, get(opts, "experiments", string(limit)))
        repeats = parse(Int, get(opts, "repeats", "32"))
        1 <= batches <= limit || error("$study supports 1..$limit experiments")
        1 <= repeats <= 32 || error("repeats must be in 1..32")
        for method in algs, parameter in parameters, d in distances
            push!(jobs, (study=study, scene=scene, method=method, parameter=parameter, distance=d, batches=batches, repeats=repeats))
        end
    end
    isempty(jobs) && error("Selection contains no experiments")
    jobs
end
function reference(scene, d, p)
    grid = collect(0:p.steps) .* p.dt
    scene == "canonical" && return grid, MCMLS.analytical_curve(grid, p.D, d*CFG["physics"]["R"], CFG["physics"]["R"])
    path = joinpath(ROOT, "outputs", scene, "reference", @sprintf("d%02dR.csv",d))
    raw = readdlm(path, ',', Float64; skipstart=1)
    size(raw,2) == 2 && all(isfinite,raw) && all(diff(raw[:,1]).>0) || error("Invalid reference $path")
    raw[1,1] == 0 && raw[end,1] >= p.T-1e-13 || error("Reference does not cover simulation")
    q = zeros(length(grid)); j = 1
    for i in eachindex(grid)
        while j < size(raw,1)-1 && raw[j+1,1] < grid[i]; j+=1; end
        u=(grid[i]-raw[j,1])/(raw[j+1,1]-raw[j,1]); q[i]=(1-u)*raw[j,2]+u*raw[j+1,2]
    end
    grid,q
end
function batch(s,p,settings,method,seeds,grid)
    q=zeros(length(grid),length(seeds)); estimates=Vector{Estimate}(undef,length(seeds)); elapsed=zeros(length(seeds))
    @threads for i in eachindex(seeds)
        start=time_ns(); estimates[i]=run_algorithm(method,s,p,settings,seeds[i])
        absorption_curve!(view(q,:,i),estimates[i].probability,estimates[i].taus,grid)
        elapsed[i]=(time_ns()-start)/1e9
    end
    q,estimates,elapsed
end
function tcritical95(n::Int)
    n<=1 && return NaN
    table=[12.706205,4.302653,3.182446,2.776445,2.570582,2.446912,2.364624,
        2.306004,2.262157,2.228139,2.200985,2.178813,2.160369,2.144787,2.131450,
        2.119905,2.109816,2.100922,2.093024,2.085963,2.079614,2.073873,2.068658,
        2.063899,2.059539,2.055529,2.051831,2.048407,2.045230,2.042272]
    n-1<=length(table) && return table[n-1]
    # First terms of the normal-to-Student quantile expansion.
    z=1.959963984540054;v=n-1
    z+(z^3+z)/(4v)+(5z^5+16z^3+3z)/(96v^2)
end
function bounds(mean,sd,method,n)
    if method == "monc"
        m=n*CFG["simulation"]["molecules"]; z=1.959963984540054; den=1+z*z/m
        c=(mean+z*z/(2m))/den; h=z*sqrt(mean*(1-mean)/m+z*z/(4m*m))/den
        return max(0.,c-h),min(1.,c+h)
    end
    (n<=1 || (sd==0 && (mean==0 || mean==1))) && return NaN,NaN
    h=tcritical95(n)*sd/sqrt(n)
    max(0.,mean-h),min(1.,mean+h)
end
function execute(job, opts, out, concurrency)
    ph=CFG["physics"]; sim=CFG["simulation"]
    steps=parse(Int,get(opts,"steps",string(ph["steps"]))); steps>=1 || error("steps must be positive")
    p=Physics(ph["D"],(steps==ph["steps"] ? ph["dt"] : ph["dt"]*ph["steps"]/steps),steps)
    scene=build_scene(TOML.parsefile(joinpath(ROOT,"config/scenes/$(job.scene).toml")),Float64(job.distance),ph["R"])
    grid,ref=reference(job.scene,job.distance,p)
    settings=Dict{String,Any}("M"=>sim["molecules"],"N_replica"=>sim["replicas"],"step_R"=>0.5,
        "level_count"=>(job.study=="uniform-scan" ? job.parameter : sim["threshold_points"]),
        "n_worst"=>(job.study=="adaptive-scan" ? job.parameter : sim["n_worst"]),"max_iterations"=>sim["max_iterations"])
    source=joinpath(ROOT,"outputs",dataset(job.scene,job.study),"seeds.csv")
    seedrows=filter(r->r["algorithm"]==job.method && parse(Float64,r["distance_R"])==job.distance &&
        (!haskey(r,"parameter") || parse(Int,r["parameter"])==job.parameter),readcsv(source))
    seeds=Dict((parse(Int,r["experiment"]),parse(Int,r["repeat"]))=>parse(UInt64,r["seed_hex"];base=16) for r in seedrows)
    tag=@sprintf("d%02dR",job.distance)
    folder=joinpath(out,dataset(job.scene,job.study),"runs",job.method,tag,"p$(job.parameter)")
    # Source and seed identities make an interrupted run safe to resume.
    identity=string(job,p.D,p.dt,p.steps,sort(collect(settings);by=first),VERSION,nthreads(),concurrency)
    code=vcat(read(joinpath(ROOT,"config/paper.toml")),read(joinpath(ROOT,"config/scenes/$(job.scene).toml")))
    for f in ["MCMLS.jl","core.jl","algorithms/fixed.jl","algorithms/ams_mod.jl","simulate.jl"]
        append!(code,read(joinpath(ROOT,"src",f)))
    end
    append!(code,codeunits(identity)); append!(code,read(source)); append!(code,reinterpret(UInt8,ref))
    fp=bytes2hex(sha256(code))
    samples=unique(round.(Int,range(1,length(grid);length=min(sim["curve_points"],length(grid)))))
    for b in 1:job.batches
        target=joinpath(folder,@sprintf("e%02d",b)); meta=joinpath(target,"run.toml")
        if isfile(meta)
            st=TOML.parsefile(meta)
            st["fingerprint"]==fp || error("Existing run configuration differs: $target")
            all(bytes2hex(sha256(read(joinpath(target,f))))==h for (f,h) in st["files"]) || error("Incomplete saved batch: $target")
            println("SKIP $(job.study) $(job.scene) $(job.method) $tag e$b"); continue
        end
        ispath(target) && error("Incomplete batch directory: $target")
        warm=Physics(p.D,p.T/min(p.steps,200),min(p.steps,200)); small=copy(settings)
        small["M"]=24;small["N_replica"]=24;small["n_worst"]=min(small["n_worst"],23)
        batch(scene,warm,small,job.method,[stable_seed("warmup",job.study,job.method,job.distance,b)],collect(0:warm.steps).*warm.dt)
        GC.gc()
        ss=[seeds[b,i] for i in 1:job.repeats]
        measured=@timed batch(scene,p,settings,job.method,ss,grid)
        q,estimates,elapsed=measured.value
        any(r->r.completion=="iteration_cap",estimates) && error("Adaptive iteration cap reached")
        qm=vec(mean(q;dims=2)); sd=job.repeats>1 ? vec(std(q;dims=2)) : fill(NaN,length(grid))
        denom=sum(abs2,ref); mse=sum(abs2,qm.-ref)/denom
        counts=[e.counters for e in estimates]
        row=Any[job.scene,job.distance,job.method,job.parameter,b,job.repeats,true,sqrt(mse),mse,measured.time,qm[end],ref[end],0,
            sum(c.propagation+c.replay for c in counts),sum(c.propagation for c in counts),sum(c.replay for c in counts),sum(c.clones for c in counts),count(e->isempty(e.taus),estimates)/job.repeats]
        mkpath(dirname(target)); temp=mktempdir(dirname(target);prefix=".batch-")
        try
            writecsv(joinpath(temp,"experiment.csv"),FIELDS,[row])
            cr=[]
            for j in samples
                lo,hi=bounds(qm[j],sd[j],job.method,job.repeats)
                push!(cr,vcat([grid[j],ref[j],qm[j],sd[j],lo,hi],q[j,:]))
            end
            writecsv(joinpath(temp,"curves.csv"),vcat(["t","q_ref","q_mean","q_std","ci95_lower","ci95_upper"],["q_repeat_$i" for i in 1:job.repeats]),cr)
            rr=[];taus=[]
            for i in eachindex(estimates)
                e=estimates[i];c=e.counters;err=sum(abs2,q[:,i].-ref)/denom
                push!(rr,[i,string(ss[i];base=16,pad=16),e.probability,err,c.propagation+c.replay,c.propagation,c.replay,c.clones,c.iterations,length(e.taus),e.completion,elapsed[i]])
                for t in e.taus; push!(taus,[i,t]); end
            end
            writecsv(joinpath(temp,"repeats.csv"),["repeat","seed_hex","P_hat","relative_mse","total_steps","propagation_steps","replay_steps","clones","iterations","n_hit","completion_status","elapsed_seconds"],rr)
            writecsv(joinpath(temp,"taus.csv"),["repeat","tau"],taus)
            files=Dict(f=>bytes2hex(sha256(read(joinpath(temp,f)))) for f in ["experiment.csv","curves.csv","repeats.csv","taus.csv"])
            open(joinpath(temp,"run.toml"),"w") do f
                TOML.print(f,Dict("fingerprint"=>fp,"julia"=>string(VERSION),"threads"=>nthreads(),"concurrent_jobs"=>concurrency,"steps"=>p.steps,"dt"=>p.dt,"files"=>files))
            end
            mv(temp,target)
        finally
            ispath(temp) && rm(temp;recursive=true)
        end
        @printf("DONE %-13s %-16s %-7s %s p=%d e=%d/%d error=%.6g wall=%.3fs\n",job.study,job.scene,job.method,tag,job.parameter,b,job.batches,sqrt(mse),measured.time)
        flush(stdout)
    end
end
function aggregate(out,jobs)
    for rel in unique([dataset(j.scene,j.study) for j in jobs])
        directory=joinpath(out,rel); data=Dict{String,String}[]
        for (dir,dirs,files) in walkdir(joinpath(directory,"runs"))
            # A killed worker can leave .batch-* staging directories behind.
            # Only aggregate committed batches with their completion manifest.
            filter!(name->!startswith(name,"."),dirs)
            "run.toml" in files && "experiment.csv" in files && append!(data,readcsv(joinpath(dir,"experiment.csv")))
        end
        sort!(data;by=r->(r["algorithm"],parse(Float64,r["distance_R"]),parse(Int,r["parameter"]),parse(Int,r["experiment"])))
        writecsv(joinpath(directory,"experiments.csv"),FIELDS,[[r[k] for k in FIELDS] for r in data])
    end
end
function main(args=ARGS)
    opts=options(args)
    if haskey(opts,"help")
        println("Paper simulations: --study main|cdf|uniform-scan|adaptive-scan|all")
        println("--scenes CSV --methods monc,mls_lb,ams_mod --distances CSV --parameters CSV")
        println("--experiments N --repeats N --steps N --jobs N --output-root PATH --dry-run")
        println("Defaults: paper parameters; JOBS=2; THREADS=32; outputs/rerun")
        return
    end
    VERSION>=v"1.11" || error("Julia 1.11 or newer is required")
    jobs=plan(opts); concurrency=parse(Int,get(opts,"jobs",get(ENV,"JOBS","2")))
    concurrency>=1 || error("jobs must be positive")
    out=abspath(ROOT,get(opts,"output-root","outputs/rerun"))
    archived=joinpath(ROOT,"outputs")
    (out==archived || any(out==joinpath(archived,s) || startswith(out,joinpath(archived,s)*"/") for s in vcat(SCENES,["figures","analysis"]))) && error("Choose a separate output root")
    # Fail early if any required FEM reference is absent or malformed.
    ph=CFG["physics"]; steps=parse(Int,get(opts,"steps",string(ph["steps"]))); steps>=1 || error("steps must be positive")
    p=Physics(ph["D"],(steps==ph["steps"] ? ph["dt"] : ph["dt"]*ph["steps"]/steps),steps)
    for (s,d) in unique([(j.scene,j.distance) for j in jobs]); reference(s,d,p); end
    if haskey(opts,"worker")
        index=parse(Int,opts["worker"]); execute(jobs[index],opts,out,jobs[index].method=="monc" ? 1 : concurrency); return
    end
    @printf("%d cases, %d batches, %d estimator runs; %d threads per worker\n",length(jobs),sum(j.batches for j in jobs),sum(j.batches*j.repeats for j in jobs),nthreads())
    if haskey(opts,"dry-run")
        for j in jobs; println(j); end
        return
    end
    println("Output: $out")
    # MonC uses one job; each A-MLS study uses up to JOBS simultaneous workers.
    for study in unique([j.study for j in jobs]), monc in [true,false]
        indices=findall(j->j.study==study && (j.method=="monc")==monc,jobs)
        sem=Base.Semaphore(monc ? 1 : concurrency)
        @sync for index in indices
            @async begin
                Base.acquire(sem)
                try
                    cmd=`$(Base.julia_cmd()) --startup-file=no --threads=$(nthreads()) --project=$ROOT $(@__FILE__) $args --worker $index`
                    run(cmd)
                finally
                    Base.release(sem)
                end
            end
        end
    end
    aggregate(out,jobs)
    println("Simulation complete. Analyze with: python3 tools/analyze.py --data-root $out")
end
try
    main()
catch e
    showerror(stderr,e,catch_backtrace());println(stderr);exit(1)
end
