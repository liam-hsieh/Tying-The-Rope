function Loading = ObserveLoading(obj, mat_name, q, cov, export)
% this method evaluate input matrix by unbiased demand mean, high and low scenario

n = obj.Pars.num_prod;
m = obj.Pars.num_site;

average_demand = obj.Demand.rv_mean(:, q);
high_demand = obj.Demand.rv_mean(:, q).*(1+cov);
low_demand = obj.Demand.rv_mean(:, q).*(1-cov);

demands = [average_demand, high_demand, low_demand];
x_matrix = cell(1,3);

for i = 1:3
    LP = obj.PrepareLP(mat_name, q, demands):, i));
    [x, ~] = obj.RunLP(LP);
    
    var_x = transpose(reshape(transpose(x(1:n*m)), m, n));
    x_matrix{1, i} = transpose(reshape(transpose(var_x), m, n));
end

if export ==true
    filename = ['loading_' char(mat_name)];
    sht_name = ['average', 'high','low'];
    
    for i=1:3
        obj.Export2Excel(x_matrix{1,i}, obj.BasicInfo.product, obj.BasicInfo.site, obj.Dir.output,  filename, sht_name(i));
    end
    
end
Loading = x_matrix;
end