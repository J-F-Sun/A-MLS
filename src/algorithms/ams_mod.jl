mutable struct ReplayPath
    start_x::Point
    start_step::Int
    start_rng::Xoshiro
    endpoint::Particle
    best_distance2::Float64
end
function finish_path!(r::Particle,s::Scene,p::Physics,c::Counters)
    best=distance2(r.x,s.center)
    while r.status==ALIVE && r.step<p.steps
        step!(r,s,p);c.propagation+=1;c.score_evaluations+=1
        # A competing absorption cannot create a new branching checkpoint.
        # Keep the best progress strictly before this killing boundary.
        r.status!=COMPETITOR && (best=min(best,distance2(r.x,s.center)))
    end
    r.status==TARGET ? s.radius^2 : best
end

"""RNG replay of the parent suffix to its first STRICT crossing.

Every replayed Brownian step is included in the cost, even though it duplicates
an already simulated prefix. No full coordinate trajectory is retained.
"""
function replay_crossing(parent::ReplayPath,level::Float64,s::Scene,p::Physics,c::Counters)
    r=Particle(parent.start_x,parent.start_step,ALIVE,NaN,copy(parent.start_rng),parent.endpoint.ancestor)
    while true
        # A replay checkpoint can itself already overshoot this new threshold.
        if inside(r.x,s.center,s.radius)
            r.status=TARGET;r.tau=r.step*p.dt;return r
        end
        distance2(r.x,s.center)<level && return r
        r.status==ALIVE && r.step<p.steps || error("parent did not strictly cross selected threshold")
        step!(r,s,p);c.replay+=1;c.score_evaluations+=1
        r.status==TARGET && return r
        r.status==COMPETITOR && error("parent hit competitor before its recorded crossing")
    end
end
function selection(scores::Vector{Float64},k::Int)
    1<=k<length(scores) || error("n_worst must be in 1..N-1")
    level=partialsort(scores,k;rev=true)
    killed=findall(>=(level),scores) # include every tie at the selected threshold
    survivors=findall(<(level),scores)
    level,killed,survivors
end

"""Adaptive A-MLS mechanism: bulk kills + RNG-replayed branching checkpoints.

Discrete-time corrections: kill all boundary ties, use actual killed fraction,
strict crossing, and carry terminal absorption states without revival.
"""
function run_ams_mod(s::Scene,p::Physics,N::Int,n_worst::Int,max_iterations::Int,seed::UInt64)
    1<=n_worst<N || error("n_worst must be in 1..N-1")
    max_iterations>=1 || error("max_iterations must be >=1")
    c=Counters();paths=ReplayPath[]
    for i in 1:N
        r=fresh_particle(s,seed,i); initial_rng=copy(r.rng)
        best=finish_path!(r,s,p,c)
        push!(paths,ReplayPath(s.tx,0,initial_rng,r,best))
    end
    logweight=0.
    completion="iteration_cap"
    for iter in 1:max_iterations
        scores=[q.best_distance2 for q in paths]
        level,killed,survivors=selection(scores,n_worst)
        # Stop before killing absorbed paths; remaining exact hit fraction settles
        # the normalizing weight, including when fewer than n_worst failures remain.
        if level<=s.radius^2
            completion="completed";break
        end
        if isempty(survivors)
            return Estimate(0.,-Inf,Float64[],N,c,"extinct",0)
        end
        nk=length(killed);logweight+=log1p(-nk/N)
        c.iterations+=1
        push!(c.diagnostics,Dict("stage"=>iter,"threshold"=>level,"successes"=>length(survivors),
            "terminal_successes"=>count(q->q.endpoint.status==TARGET,paths),"killed"=>nk,
            "survival_fraction"=>length(survivors)/N,"clones_before"=>c.clones,
            "propagation_steps"=>c.propagation,"replay_steps"=>c.replay))
        rng=Xoshiro(stable_seed(seed,"ams_parent_selection",iter))
        for i in killed
            parent=paths[rand(rng,survivors)]
            child=replay_crossing(parent,level,s,p,c)
            c.clones+=1
            new_rng=Xoshiro(stable_seed(seed,"ams_child",iter,i,c.clones))
            suffix_start_rng=copy(new_rng)
            start_x=child.x;start_step=child.step
            if child.status==TARGET
                # Duplicate the observed terminal event with its original tau.
                child.rng=new_rng;best=s.radius^2
            else
                child.rng=new_rng
                best=finish_path!(child,s,p,c)
            end
            paths[i]=ReplayPath(start_x,start_step,suffix_start_rng,child,best)
        end
    end
    if completion=="iteration_cap" && partialsort([q.best_distance2 for q in paths],n_worst;rev=true)<=s.radius^2
        completion="completed"
    end
    # At a cap all suffixes are still complete paths; report the remaining target
    # fraction rather than pretending every particle was a target hit.
    estimate_from_population([q.endpoint for q in paths],logweight,N,c,completion)
end

function run_algorithm(name::String,s::Scene,p::Physics,settings::AbstractDict,seed::UInt64)
    if name=="monc"
        return run_monc(s,p,Int(settings["M"]),seed)
    elseif name=="mls_lb"
        levels=distance_levels(sqrt(distance2(s.tx,s.center)),s.radius,Float64(settings["step_R"]);count=Int(settings["level_count"]))
        return run_fixed(s,p,Int(settings["N_replica"]),levels,:distance,seed)
    elseif name=="ams_mod"
        return run_ams_mod(s,p,Int(settings["N_replica"]),Int(settings["n_worst"]),Int(settings["max_iterations"]),seed)
    end
    error("unknown algorithm $name")
end
