function [BestLink, Qmat_NextBest] = TheNextBest(obj, mat_name, priorBestObj)
%% based on the input matrix name, determine the best link to add

n = obj.Pars.num_prod;
m = obj.Pars.num_site;
q = obj.Setting.Ref_quarter;

Options = obj.CheckOptions(obj.Qmat.(mat_name));
Qarray = obj.Qmat.(mat_name);

results = cell(size(Options, 1), 1);
num_options = size(Options,1);
Options(:, 4) = zeros(num_options, 1);

for i=1:num_options
    
    Qarray_alt = Qarray; %initiate alternative Qarray
    prod_ix = Options(i, 1);
    site_ix = Options(i, 2);
    Qarray_alt(prod_ix, site_ix) = 1;
    obj.Qmat.('temp') = Qarray_alt; % write alternative Qarray to temp
    RS = obj.Evaluate('temp', q, false); % evaluate alternative Qarray
    
    Options(i, 4) = obj.Stat(q).('temp').Obj_mean; %insert mean objective value
    %Options(i, 4) = obj.Stat(q).('temp').SL.mean;
    
    results{i, 1} = RS;
end


%%%% apply the concept of primary/secondary options, comment the whole
%%%% sectio if it is no longer required
% best_primary = max(Options(Options(:,3)==1, 4)); %best objectvie value over primary options
% best_secondary = max(Options(Options(:,3)==2, 4)); %best objectvie value over secondary options
% delta = (best_primary - priorBestObj) / priorBestObj;
%
% if ((delta < obj.Setting.th_value) && (best_primary < best_secondary))
%%       consider secondary if delta is less than threshold
%       best_option_ix = find(Options(:,4) == best_secondary);
% else
%%       when options from primary can keep contributing on objecitve, go primary
%       best_option_ix = find(Options(:,4) == best_primary);
% end


[~, best_option_ix] = max(Options(:, 4));
BestLink = results{best_option_ix, 1};

BestLink{3} = Options(best_option_ix, 1);
BestLink{4} = Options(best_option_ix, 2);
BestLink{5} = Options(best_option_ix, 3);

%=========  add the next best to Qmat ========
Qmat_NextBest = Qarray; %initiate alternative Qarray
Qmat_NextBest(BestLink{3}, BestLink{4}) = 1; %prod_ix and site_ix from Best_Link
