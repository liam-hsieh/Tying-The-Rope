function LP = PrepareLP(obj, mat_name, q, demand, varargin)
%mat_name: matrix name
%q: quarter index
%demand: demand scenario

bigM = 1000;
mode = obj.Setting.mode;

if nargin>5
    error('too many input args!');
elseif nargin==5
    mode = varargin{1};
end

n = obj.Pars.num_prod;
m = obj.Pars.num_site;


%% Initiate objective
%if mode=='LP'
if strcmp(mode,'LP')
    margin_matrix = repmat(obj.Demand.margin, [1,m]);
    f_x = reshape(transpose(margin_matrix - obj.Setting.cost_matrix), [],1);
    f_u = -ones(m,1) * obj.Setting.wt_minUObj;
    f = vertcat(f_x, f_u);

elseif strcmp(mode,'MIP')
    margin_matrix = repmat(obj.Demand.margin, [1,m]);
    f_x = reshape(transpose(margin_matrix - obj.Setting.cost_matrix), [],1);
    f_y = zeros(m,1);
    f_u = -ones(m,1) * obj.Setting.wt_minUObj;
    f = vertcat(f_x, f_u);
    
end

%% left-hand-side

%if mode=='LP'
if strcmp(mode,'LP')
    %% cons (III-1)
    v1 = 1:n;
    row_indices = reshape(transpose(repmat(transpose(v1), [1,m])), 1, []);
    col_indices = 1:n*m;
    cons1_LHS = sparse(row_indices, col_indices,ones(n,m), n, n*m+m);
    
    %% cons (III-2)
    v2 = ones(1,m);
    cons2_LHS = repmat(diag(v2), 1, n);
    cons2_LHS = horzcat(cons2_LHS, zeros(m,m));
    
    %% cons (III-3)
    cons3_LHS = repmat(diag(v2), 1, n);
    cons3_LHS = horzcat(cons3_LHS, diag(v2));
    
    LHS = vertcat(cons1_LHS, cons2_LHS, -cons3_LHS);
%elseif mode=='MIP'
elseif strcmp(mode,'MIP')
    %% cons (II-1)
    v1 = 1:n;
    row_indices = reshape(transpose(repmat(transpose(v1), [1,m])), 1, []);
    col_indices = 1:n*m;
    cons1_LHS = sparse(row_indices, col_indices,ones(n,m), n, n*m+2*m); %has extra m items than cons (I-1) because of variable y_j
    
    %% cons (II-2)
    v2 = ones(1,m);
    cons2_LHS = repmat(diag(v2), 1, n);
    cons2_LHS = horzcat(cons2_LHS, zeros(m,2*m));
    
    %% cons (II-3)
    cons3_LHS = horzcat(repmat(diag(v2), 1, n), diag(v2)*bigM, zeros(m,m));% here, use horzcat concatenate three parts: 1. all x_ij 2.y_j 3. u_j
    
    %% cons (II-4)
    cons4_LHS = horzcat(repmat(diag(v2),1,n), -diag(v2)*bigM, diag(v2));
    
    
    LHS = vertcat(cons1_LHS, cons2_LHS, -cons3_LHS, -cons4_LHS);
end

%Initiate upper and lower bound
%here, 999 is just a relatively huge number to narrow down the searching space
%always check your input data scale to ensure this seeting is still appropriate when rewrite or port to other platform

if strcmp(mode,'LP')
    lb = zeros(n*m+m, 1);
    ub_x = reshape(transpose(obj.Qmat.(mat_name)), [], 1)*999;
    ub_u = ones(m, 1)*999;
    ub = vertcat(ub_x, ub_u);
elseif strcmp(mode,'MIP')
    lb = zeros(n*m +2*m, 1);
    ub_x = reshape(transpose(obj.Qmat.(mat_name)),[], 1)*999;
    ub_y = ones(m, 1);
    ub_u = obj.Capacity(:,q);
    ub = vertcat(ub_x, ub_y, ub_u);
    intcon(n*m+1):(n*m+m); %indices of y_j (binary variables)
end

%initiate LP right-hand-side
if strcmp(mode,'LP')
    min_loads = obj.MinU.*obj.Capacity(:,q);
    RHS = vertcat(demand, obj.Capacity(:,q), -min_loads); %MATLAB solver is designed for minimum problem
    
    solver_options = optimizations('linprog', 'algorithm', 'interior-point', 'Display', 'off'); %the default algorithm is'dual-simplex' if not set aside
    LP = struct('obj_f', -f ... %Coefficient vector for objective function
                ,'LHS', LHS ... 
                , 'RHS', RHS ...
                ,'lb', lb ...
                ,'ub', ub ...
                ,'solver_options', solver_options...
                );
elseif strcmp(mode,'MIP')
    min_loads = obj.MinU.*obj.Capacity(:,q);
    RHS = vertcat(demand, obj.Capacity(:,q), -min_loads, -min_loads + bigM*ones(m,1));
    solver_options = optimizations('intlinprog', 'Display', 'off');
    
    LP = struct('obj_f', -f ... %Coefficient vector for objective function
                ,'LHS', LHS ... 
                , 'RHS', RHS ...
                ,'lb', lb ...
                ,'ub', ub ...
                ,'solver_options', solver_options...
                ,'integer', intcon ... %index of integer variable
                );
end




