"""Copy a stopped success, including its actual terminal state and hit time.

Terminal copies NEVER resume diffusion. Living copies receive fresh suffix RNGs.
"""
function copy_success(parent::Particle,seed::UInt64)
    Particle(parent.x,parent.step,parent.status,parent.tau,Xoshiro(seed),parent.ancestor)
end
function resample_failed!(pop::Vector{Particle},survivors::Vector{Int},failed::Vector{Int},seed::UInt64,stage::Int,c::Counters)
    isempty(survivors) && !isempty(failed) && error("cannot resample an extinct population")
    rng=Xoshiro(stable_seed(seed,"parent_selection",stage))
    for i in failed
        parent=pop[rand(rng,survivors)]
        c.clones+=1
        pop[i]=copy_success(parent,stable_seed(seed,"fixed_child",stage,i,c.clones))
    end
end

"""Fixed-population splitting with stopped Markov states (uniform distance thresholds).

Only the current first-crossing state is required. Keeping all historical level
checkpoints is unnecessary because levels are nested and propagation stops at
each current level. Discrete overshoots can satisfy later levels immediately.
"""
function run_fixed(s::Scene,p::Physics,N::Int,levels::Vector{Float64},kind::Symbol,seed::UInt64)
    N>=2 || error("N must be >=2")
    kind == :distance || error("unsupported progress kind")
    length(levels)>=2 && all(diff(levels).<0) || error("levels must strictly descend")
    pop=[fresh_particle(s,seed,i) for i in 1:N]
    counts=Counters(); logweight=0.
    for stage in 2:length(levels)
        level=levels[stage]
        survivors=Int[];failed=Int[]
        for i in 1:N
            r=pop[i]
            while true
                reached = r.status==TARGET || (r.status==ALIVE && (
                    distance2(r.x,s.center)<=level*level))
                counts.score_evaluations+=1
                reached && break
                (r.status!=ALIVE || r.step>=p.steps) && break
                step!(r,s,p);counts.propagation+=1
            end
            success = r.status==TARGET || (r.status==ALIVE && (
                distance2(r.x,s.center)<=level*level))
            push!(success ? survivors : failed,i)
        end
        ns=length(survivors); terminal=count(r->r.status==TARGET,pop)
        counts.iterations+=1
        push!(counts.diagnostics,Dict("stage"=>stage-1,"threshold"=>level,"successes"=>ns,
            "terminal_successes"=>terminal,"killed"=>length(failed),"survival_fraction"=>ns/N,
            "clones_before"=>counts.clones,"propagation_steps"=>counts.propagation,"replay_steps"=>0))
        if ns==0
            return Estimate(0.,-Inf,Float64[],N,counts,"extinct",0)
        end
        logweight+=log(ns/N)
        # All successful mass is already in the target: settle it immediately.
        if terminal==ns || stage==length(levels)
            terminal==ns || error("last level was not the target event")
            return estimate_from_population(pop,logweight,N,counts,"completed";fraction=false)
        end
        resample_failed!(pop,survivors,failed,seed,stage,counts)
    end
    error("unreachable fixed splitting termination")
end
