function Result = Evaluate(obj, mat_name, q, varargin)
% Evaluate the performance of a matrix and update obj.Stat and obj.Recordset
%% q: index of quarter
%% mat_name: matrix name in obj.Qmat
%% This method will update obj.Stat(q).(mat_name) and obj.Recordset(q).(mat_name)

% Check for the number of input arguments
if nargin > 4
    error('too many input args!');
elseif nargin==4
    if islogical(varargin{1})
        keep_raw = varargin{1};
    else
        error('only allows logical value!');
    end
elseif nargin==3
    keep_raw = false;
end

% Extract relevant parameters
n = obj.Pars.num_prod;
m = obj.Pars.num_site;
min_loads = obj.MinU.*obj.Capacity(:,q);

%% Initialize matrices and variables
%% Initiate loop variable and matrices (SL, loading, and objective value matrices)
run_used = 0;
run =0;

SL =zeros(1, obj.Setting.num_scenario);
SL_prod =zeros(n, obj.Setting.num_scenario);
Ld_Site =zeros(m, obj.Setting.num_scenario);
Obj_value =zeros(1, obj.Setting.num_scenario);
Acc_x = single(zeros(n*m));
Acc_x_sq = single(zeros(n*m));
x_mat = zeros(m,n);
%u_slack = zeros(1,n);

if keep_raw, LPs=cell(1, obj.Setting.num_scenario);,end;

% Get dataset for solving LP
LP = obj.PrepareLP( mat_name, q ,obj.Demand.rv_mean(:,q));

while (run_used < obj.Setting.num_scenario)
    run = run+1;
    run_used = run_used +1;
    
    % Solve LP
    d = obj.RandDemand{q}(:,run); % take the next demand scenario
    lp = obj.DemandUpdate(LP, d);
    [x, fval] = obj.RunLP(lp);
    
    % Check if LP solution is empty
    if (isempty(x))
        run_used = run_used-1;
        continue;
    end
    
    % Store LP if requested
    if keep_raw, LPs{run_used} = LP;, end;
    
    % Process LP solution
    x = single(x); %here, x returned from solver is the solved values of decision variable (both x_ij and u_j in  model)
    
    % Update matrices and variables
    Acc_x = Acc_x + x(1:n*m);
    Acc_x_sq = Acc_x_sq + x(1:n*m).*x(1:n*m);
    
    x_mat = transpose(reshape(transpose(x(1:n*m)), m, n));     % the first n*m represent x_ij; 
    %u_slack = x(n*m+1:end);                                    % the last m is u_j (from n*m+1 to the end)
    site_loads = repmat(diag(ones(1,m)),1,n)*x(1:n*m);
    nSites_Loadenough = size(find(site_loads >= min_loads),1);
    
    
    % Calculate performance metrics
    SL(run_used) = sum(sum(x_mat))./sum(d);
    SL_Prod_temp = sum(x_mat,2)./d;
    SL_Prod_temp(isinf(SL_Prod_temp) | isnan(SL_Prod_temp)) = 1.0;
    SL_Prod(:, run_used) = SL_Prod_temp;
    Ld_site(:, run_used) = transpose(sum(x_mat,1)); %Site load
    Obj_Value(run_used) = -fval; %objective value
%     if run_used==50, display(Ld_site),end;
end

% Calculate mean and sigma of decision variable x
x_mean = Acc_x(1:n*m) / run_used;
x_sigma = sqrt(Acc_x_sq(1:n*m)/run_used - x_mean.*x_mean);
Obj_value_mean = mean(Obj_Value);
variable_x = struct('mean',x_mean, 'sigma',x_sigma);

% Calculate service levels and load percentages
service_level = struct('mean', mean(SL) ...
                        ,'P5', prctile(SL,5)...
                        ,'P10', prctile(SL, 10) ...
                        );

service_level_prod = struct('mean', mean(SL_Prod,2) ...
                        ,'P5', prctile(SL_Prod,5, 2)...
                        ,'P10', prctile(SL_Prod, 10,2) ...
                        );
load_site_percent = struct('mean', mean(Ld_Site,2)./obj.Capacity(:,q) ...
                        ,'P5', prctile(Ld_Site,5,2)./obj.Capacity(:,q)...
                        ,'P10', prctile(Ld_Site, 10,2)./obj.Capacity(:,q) ...
                        );

% Update obj.Stat with the evaluation results
obj.Stat(q).(mat_name) = struct('SL', service_level ...
                                ,'SL_prod', service_level_prod ...
                                ,'U_site', load_site_percent ...
                                ,'Obj_mean', Obj_value_mean ...
                                ,'Var_x', variable_x ... 
                                );
% Format the Result variable for compatibility with BestLink
%% format of Result is same as BestLink, the return variable of method TheNextBest
num_link = sum(obj.Qmat.(mat_name), 'all'); % number of links

Result = [ 
            {mat_name num_link 0 0 '' Obj_value_mean service_level.mean } ...
            num2cell(transpose(load_site_percent.mean)) ...
            num2cell(transpose(load_site_percent.P10)) ...
            num2cell(transpose(load_site_percent.P5))...
        ];
    
%% record to Recordset
if keep_raw
    Raw = struct ('LP', LPs, 'SL', SL, 'SL_Prod', SL_Prod, 'Ld_Site', Ld_Site, 'Obj_Value', Obj_Value);
    obj.Recordset(q).(mat_name) = Raw;
end

          
                        



                    
