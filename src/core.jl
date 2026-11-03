const Point = NTuple{3,Float64}
const ALIVE = UInt8(0)
const TARGET = UInt8(1)
const COMPETITOR = UInt8(2)
@inline add(a::Point,b::Point) = (a[1]+b[1],a[2]+b[2],a[3]+b[3])
@inline sub(a::Point,b::Point) = (a[1]-b[1],a[2]-b[2],a[3]-b[3])
@inline scale(a::Point,s::Float64) = (s*a[1],s*a[2],s*a[3])
@inline dot3(a::Point,b::Point) = a[1]*b[1]+a[2]*b[2]+a[3]*b[3]
@inline distance2(a::Point,b::Point) = dot3(sub(a,b),sub(a,b))
@inline inside(x::Point,c::Point,r::Float64) = distance2(x,c)<=r*r

struct Scene
    name::String
    distance_R::Float64
    tx::Point
    center::Point
    radius::Float64
    obstacle::Union{Nothing,Point}
    obstacle_radius::Float64
    competitor::Union{Nothing,Point}
    competitor_radius::Float64
end
struct Physics
    D::Float64
    dt::Float64
    steps::Int
    sigma::Float64
    T::Float64
end
function Physics(D::Real,dt::Real,steps::Integer)
    isfinite(D) && D>0 || error("D must be positive and finite")
    isfinite(dt) && dt>0 || error("dt must be positive and finite")
    steps>=1 || error("steps must be positive")
    Physics(Float64(D),Float64(dt),Int(steps),sqrt(2.0*D*dt),steps*dt)
end
mutable struct Particle
    x::Point
    step::Int
    status::UInt8
    tau::Float64
    rng::Xoshiro
    ancestor::Int
end
mutable struct Counters
    propagation::Int
    replay::Int
    clones::Int
    iterations::Int
    score_evaluations::Int
    diagnostics::Vector{Dict{String,Any}}
end
Counters() = Counters(0,0,0,0,0,Dict{String,Any}[])
struct Estimate
    probability::Float64
    log_probability::Float64
    taus::Vector{Float64}
    initial_particles::Int
    counters::Counters
    completion::String
    hit_ancestors::Int
end

"""Portable seed schema v1: SHA-256 of length-delimited UTF-8 components.

Never uses Julia's process/version-dependent hash(). Log every repeat seed.
Exact RNG replay requires the recorded Julia version and this source version.
"""
function stable_seed(parts...)
    io=IOBuffer()
    for p in parts
        s = p isa AbstractFloat ? @sprintf("%.17g",p) : string(p)
        print(io,ncodeunits(s),':',s,';')
    end
    bytes=sha256(take!(io)); result=UInt64(0)
    for b in bytes[1:8]; result=(result<<8)|UInt64(b); end
    result
end
fresh_particle(scene::Scene,seed::UInt64,i::Int) = Particle(scene.tx,0,ALIVE,NaN,Xoshiro(stable_seed(seed,"initial",i)),i)

function build_scene(cfg::AbstractDict,dR::Float64,R::Float64)
    ds=Float64.(cfg["distances_R"]); index=findfirst(==(dR),ds)
    index===nothing && error("distance $dR is not configured for $(cfg["name"])")
    g=cfg["geometry"]; d=dR*R
    function offset(key,default)
        v=get(g,key,default)
        if v isa AbstractVector
            length(v)==length(ds) || error("offset array has wrong length")
            return Float64(v[index])
        end
        Float64(v)
    end
    obstacle=nothing; competitor=nothing; ro=0.; rc=0.
    if cfg["kind"]=="obstacle"
        obstacle=(offset("obstacle_offset_x_R",.5)*d,offset("obstacle_offset_y_R",0.)*R,0.)
        ro=offset("obstacle_radius_R",1.)*R
    elseif cfg["kind"]=="two_receiver"
        competitor=(offset("competitor_offset_x_R",.5)*d,offset("competitor_offset_y_R",2.5)*R,0.)
        rc=offset("competitor_radius_R",1.)*R
    elseif cfg["kind"]!="canonical"
        error("unsupported scene kind")
    end
    s=Scene(cfg["name"],dR,(d,0.,0.),(0.,0.,0.),offset("target_radius_R",1.)*R,obstacle,ro,competitor,rc)
    s.radius>0 || error("target radius must be positive")
    inside(s.tx,s.center,s.radius) && error("TX is inside target")
    for (c,r) in [(obstacle,ro),(competitor,rc)]
        c===nothing && continue
        r>0 || error("extra sphere radius must be positive")
        sqrt(distance2(c,s.center))>r+s.radius || error("sphere boundaries overlap/touch")
        inside(s.tx,c,r) && error("TX is inside an extra sphere")
    end
    s
end

"""Specular reflection of a full straight displacement at one convex sphere.

Unlike endpoint-only reflection, this also detects a segment passing through
the obstacle and exiting again. This remains a discrete Brownian approximation.
"""
function reflect_segment(old::Point,new::Point,c::Point,r::Float64)
    delta=sub(new,old); oc=sub(old,c); a=dot3(delta,delta)
    a==0 && return old
    b=dot3(oc,delta); cc=dot3(oc,oc)-r*r
    cc < -1e-10*r*r && error("walk started inside reflecting sphere")
    # The closest point on this segment is outside: no intersection/root work.
    u=clamp(-b/a,0.,1.)
    distance2(add(old,scale(delta,u)),c) >= r*r*(1-8eps(Float64)) && return new
    disc=max(0.,b*b-a*cc)
    t=(-b-sqrt(disc))/a
    t=clamp(t,0.,1.)
    hit=add(old,scale(delta,t)); normal=scale(sub(hit,c),1/sqrt(distance2(hit,c)))
    tail=scale(delta,1-t)
    reflected=sub(tail,scale(normal,2dot3(tail,normal)))
    candidate=add(add(hit,reflected),scale(normal,1e-12*r))
    if inside(candidate,c,r)
        q=sub(candidate,c); qn=sqrt(dot3(q,q))
        candidate=add(c,scale(qn==0 ? normal : q,(r*(1+1e-12))/(qn==0 ? 1. : qn)))
    end
    candidate
end

"""Shared discrete transition: Gaussian step, reflector, endpoint absorption.

Target and competitor are disjoint, so endpoint classification is unambiguous.
Finite-step absorption is NOT a Brownian-bridge-exact continuous-time method.
"""
@inline function advance(x::Point,p::Physics,rng::Xoshiro,s::Scene)
    y=(x[1]+p.sigma*randn(rng),x[2]+p.sigma*randn(rng),x[3]+p.sigma*randn(rng))
    if s.obstacle!==nothing
        y=reflect_segment(x,y,s.obstacle::Point,s.obstacle_radius)
    end
    inside(y,s.center,s.radius) && return y,TARGET
    if s.competitor!==nothing && inside(y,s.competitor::Point,s.competitor_radius)
        return y,COMPETITOR
    end
    y,ALIVE
end
@inline function step!(r::Particle,s::Scene,p::Physics)
    r.status==ALIVE || error("attempt to propagate a terminal replica")
    r.step+=1; r.x,r.status=advance(r.x,p,r.rng,s)
    r.status==TARGET && (r.tau=r.step*p.dt)
    nothing
end

function distance_levels(d::Float64,R::Float64,spacing_R::Float64;count::Int=0)
    d>R>0 || error("distance levels require d>R>0")
    count==0 || count>=2 || error("distance level count must be 0 or >=2")
    count>=2 && return collect(range(d,R;length=count))
    isfinite(spacing_R) && spacing_R>0 || error("spacing_R must be positive")
    step=spacing_R*R; n=ceil(Int,(d-R)/step)
    n<=100000 || error("too many distance levels")
    tol=64eps(max(d,R))
    levels=[d-j*step for j in 0:max(0,n-1) if d-j*step>R+tol]
    push!(levels,R)
    all(diff(levels).<0) || error("distance levels must be strictly decreasing")
    levels
end

function estimate_from_population(pop,log_weight,N,counters,completion;fraction=true)
    hit=[r for r in pop if r.status==TARGET]
    prob=isempty(hit) ? 0. : exp(log_weight)*(fraction ? length(hit)/N : 1.)
    logprob=prob==0 ? -Inf : log(prob)
    Estimate(prob,logprob,[r.tau for r in hit],N,counters,completion,length(unique([r.ancestor for r in hit])))
end
function absorption_curve!(q::AbstractVector{Float64},prob::Float64,taus::Vector{Float64},grid)
    fill!(q,0.); isempty(taus) && return q
    sorted=sort(taus); j=0
    for i in eachindex(grid)
        while j<length(sorted) && sorted[j+1]<=grid[i];j+=1;end
        q[i]=prob*j/length(sorted)
    end
    q
end
function run_monc(s::Scene,p::Physics,M::Int,seed::UInt64)
    M>0 || error("M must be positive")
    counts=Counters(); taus=Float64[]; ancestors=Int[]
    for i in 1:M
        r=fresh_particle(s,seed,i)
        while r.status==ALIVE && r.step<p.steps
            step!(r,s,p); counts.propagation+=1
        end
        if r.status==TARGET;push!(taus,r.tau);push!(ancestors,i);end
    end
    prob=length(taus)/M
    Estimate(prob,prob==0 ? -Inf : log(prob),taus,M,counts,"completed",length(ancestors))
end

@inline erfc64(x::Float64) = ccall((:erfc,Base.Math.libm),Float64,(Float64,),x)
function analytical_curve(grid,D,d,R)
    [t<=0 ? 0. : (R/d)*erfc64((d-R)/sqrt(4D*t)) for t in grid]
end
