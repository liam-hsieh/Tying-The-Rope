classdef Tying_The_Rope < handle
    %UNTITLED Summary of this class goes here
    %   Detailed explanation goes here
    
    properties (SetAccess = public)
        % Properties related to the Tying_The_Rope class
        BasicInfo
        Pars
        Qmat
        Dir
        Demand
        MinU
        Capacity
        Setting
        RandDemand
        Recordset
        Stat
        Progress
        Options
       
    end
    
    methods
          function obj = Tying_The_Rope(varargin)
            % Constructor for the Tying_The_Rope class

            %%%%%%%%%%%%%% default setting %%%%%%%%%%%%%%
            %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            mode = 'LP'; %'LP' or 'MIP'
            
            margin = false;
            load_priority = true;
            th_value = 0.003;
            alpha = 0.8;
            Obj_tol = 1e-5; % Changed to scientific notation
            SL_tol = 1e-5;  % Changed to scientific notation
            PctOf_SL_full_Target = 1;
            wt_minUObj = 0.2;
            
            %%%%  section for keeping raw data %%%%%%%%%%
            %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            other_quarters = true;
            ref_quarters  =true;
            added_links = true;
            
            sl_target = 0;
            maxround = 20;
            num_scenario = 30;
            
            
            %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            % Configuration struct
            configuration = struct('margin', margin...
                                   ,'load_priority', load_priority ...
                                   );
            
            % Validate input arguments
            isaninteger = @(x)isfinite(x) & x==floor(x); %an anonymous function for checking arg is interger or not
            
            if nargin > 3
                error('too many input args');
            elseif nargin==3
                if ((varargin{1}>1) || (varargin{1}<0) || (~isnumeric(varargin{1})))
                    error('target service level should be within 0 and 1');
                end
                if ((varargin{2}<0) || (~isaninteger(varargin{2})))
                    error('MaxRound requires positive integer');
                end
                if ((varargin{3}<0) || (~isaninteger(varargin{3})))
                    error('number of scenarios should be a positive interger');
                end
                sl_target = varargin{1};
                maxround = varargin{2};
                num_scenario = varargin{3};
            elseif nargin==2
                if ((varargin{1}>1) || (varargin{1}<0) || (~isnumeric(varargin{1})))
                    error('target service level should be within 0 and 1');
                end
                if ((varargin{2}<0) || (~isaninteger(varargin{2})))
                    error('MaxRound requires positive integer');
                end
                sl_target = varargin{1};
                maxround = varargin{2};
            elseif nargin==1
                if ((varargin{1}>1) || (varargin{1}<0) || (~isnumeric(varargin{1})))
                    error('target service level should be within 0 and 1');
                end
                sl_target = varargin{1};
            end
            
            % Set up object properties
            %[basicinfo pars qmat dir demand minU capacity priority_weight cost_matrix]=f_load_input_file();
            [basicinfo, pars, qmat, dir, demand, minU, capacity, priority_weight, cost_matrix] = f_load_input_file();
%             obj.BasicInfo = struct('product', {string(basicinfo.product)}...
%                                   ,'site', {string(basicinfo.site)}...
%                                   ,'quarter', {string(basicinfo.quarter)}...
%                                   );
            obj.BasicInfo = basicinfo;             
            obj.Pars = pars;
            obj.Qmat = qmat;
            obj.Dir = dir;
            obj.Demand = demand;
            obj.MinU  =minU;
            obj.Capacity = capacity;
            
            mix_idx = @(i,j) [i,j];
            [prod_ix, site_ix] = find(obj.Qmat.exclusion==0);
            primary = mix_idx(prod_ix, site_ix);
            [prod_ix, site_ix] = find(obj.Qmat.exclusion==2);
            secondary = mix_idx(prod_ix, site_ix);
            obj.Options = struct('primary', primary...
                                ,'secondary', secondary...
                                );
            
            obj.Progress = [...
                            {'name', 'num_link' 'product' 'site' 'option type' 'Obj_mean' 'SL_mean' } ...
                            cellfun(@(c)[c '_Ld_mean'], basicinfo.site, 'uni',false) ...
                            cellfun(@(c) [c '_Ld_P10'], basicinfo.site, 'uni', false)...
                            cellfun(@(c) [c, '_LdP5'], basicinfo.site, 'uni', false) ...
                            ]; %here, only add header for each column and then insert corresponding value while adding new links (for example, obj.Progress=[obj.Progress ; num2cell(ones(1,42))])
            
            obj.Recordset = struct('base', cell(1, pars.num_quarter) ...            
                                   ,'plan', cell(1, pars.num_quarter) ...      
                                   ,'max', cell(1, pars.num_quarter) ... 
                                    ); % if a new field needs to be added into Recordset later -> [obj.Recordset.('link3')] = deal({}) 
                            
                                
            obj.Stat = struct('base', cell(1, pars.num_quarter) ... 
                                   ,'plan', cell(1, pars.num_quarter) ...      
                                   ,'max', cell(1, pars.num_quarter) ... 
                                    );
            
            [~, max_quarter] = max(sum(obj.Demand.fcst, 1));
            
            obj.Setting = struct('SL_Target',sl_target ...
                                ,'MaxRound', maxround ...
                                ,'num_scenario', num_scenario ...
                                ,'Ref_quarter', max_quarter ...
                                ,'alpha_for_objective', alpha ...
                                ,'th_value', th_value ...
                                ,'tolerance', struct('Obj', Obj_tol, 'SL', SL_tol) ...
                                ,'load_priority', {priority_weight*100} ...
                                ,'cost_matrix', {cost_matrix}...
                                ,'configuration', {configuration}...
                                ,'keep_raw', struct('other_quarters', other_quarters...
                                                    ,'ref_quarters', ref_quarters ...
                                                    ,'added_links', added_links...
                                                    )...
                                ,'mode', mode ...
                                ,'PctOf_SL_full_Target', PctOf_SL_full_Target ...
                                ,'wt_minUObj', wt_minUObj ...
                                );
            
%             disp(sprintf(['set up your TTR using method initial([SL_Target, MaxRound, num_scenario, Ref_quarter]) \n\n', ...
%                 'SL_Target: target of SL \n' ...
%                 'MaxRound: maximum attempts for adding links \n' ...
%                 'num_scenario: number of demand scenario for evaluating a given qualification network \n'...
%                 'Ref_quarter: index of quarter selected as a reference for link recommendation'] ))
            
          end

          
          function CreateRandDemand(obj,varargin)
            % Method to create random demand
            if nargin>2
                error('too many input args!');
            elseif nargin==2
                load(fullfile(obj.Dir.input, varargin{1}), 'RandDemand');
                obj.RandDemand = RandDemand;
            else
                real_size = obj.Setting.num_scenario*1.2;
                
                for q =1:obj.Pars.num_quarter
                    
                    Dgen = zeros(obj.Pars.num_prod, real_size);
                    for i =1:real_size
                        Dgen(:,i) = normrnd(obj.Demand.rv_mean(:,q), obj.Demand.rv_std(:,q), obj.Pars.num_prod,1);
                    end
                    Dgen = max(Dgen, zeros(obj.Pars.num_prod, real_size)); %truncate negative demand
                    RandDemand{q} = Dgen;
                end
                save(fullfile(obj.Dir.output, 'RandDemand.mat'), 'RandDemand');
                obj.RandDemand = RandDemand;
            end
            
          end        
    end
      
    methods(Static)
        function [x, fval] = RunLP(LP)

            if isfield(LP, 'solver_options') && numel(fieldnames(LP))==6 
                [x, fval] = linprog(LP.obj_f, LP.LHS, LP.RHS, [],[], LP.lb, LP.ub, LP.solver_options);
            elseif isfield(LP, 'solver_options') && numel(fieldnames(LP))==7  
                [x, fval] = intlinprog(LP.obj_f, LP.integer, LP.LHS, LP.RHS, [],[], LP.lb, LP.ub, LP.solver_options);
            end
        end
        

        function LP = DemandUpdate(LP, new_demand)
                LP.RHS(1:size(new_demand,1), 1) =new_demand;
        end
          
        function Export2Excel(values, dir, filename, sheetname, row_label, column_label)
           if iscell(values), values = string(values);, end;
           
           if (isempty(column_label) && isempty(row_label))
               mat = values;
           elseif (~isempty(column_label) && ~isempty(row_label))
               row_label = ['' ; row_label];
               temp = [column_label ; values];
               mat = [row_label temp];
           elseif ~isempty(row_label)
               mat = [row_label values];
           elseif ~isempty(column_label)
               mat = [column_label ; values];
           end
           
           
           writematrix(mat, fullfile(dir, filename), 'Sheet', sheetname);
           %xlswrite(fullfile(dir, filename), mat, sheetname);  %for legacy verison
           
            
        end    
        
    end    
    
    
end

%function [BasicInfo Pars Qmat Dir Demand MinUtil Capacity priority_weight cost_matrix]=f_load_input_file()
function [BasicInfo, Pars, Qmat, Dir, Demand, MinUtil, Capacity, priority_weight, cost_matrix] = f_load_input_file()                
                [input_file_name, input_path] = uigetfile(...
                                                            {...
                                                                '*xlsx','xlsx (*.xlsx)';...
                                                                '*.xls','xls (*.xls)';...
                                                                '*.xlsm','xlsm (*.xlsm)';...
                                                                '*.*','All files (*.*)'...
                                                            }...
                                                            ,'Select input data'...
                                                            ,'MultiSelect','off'...
                                                            );
                if input_path==0, error('no file has been selected!'),end;
                version_name = strsplit(input_file_name, '.');
                version_name=char(version_name(1));
                
                output_dir = ['.\outputs\', version_name]; if not(isdir(output_dir)), mkdir(output_dir),end;
                interm_dir = ['.\Interms\', version_name]; if not(isdir(interm_dir)), mkdir(interm_dir),end;
                
                Dir = struct('output', output_dir...
                            ,'interm',interm_dir...
                            ,'input', input_path...
                            ,'version_name', version_name...
                            ,'input_file_name', input_file_name ...
                            );
                        
                [~, product,~]     = xlsread([input_path, input_file_name], 'BasicInfo','A:A');
                [~, site,~]        = xlsread([input_path, input_file_name], 'BasicInfo','B:B');
                [~, quarter,~]     = xlsread([input_path, input_file_name], 'BasicInfo','C:C');
                priority_weight    = xlsread([input_path, input_file_name], 'Priority');
                cost_matrix    = xlsread([input_path, input_file_name], 'Cost');
                sht_demand    = xlsread([input_path, input_file_name], 'Demand');
                sht_site    = xlsread([input_path, input_file_name], 'Site');
                Qmat_base    = xlsread([input_path, input_file_name], 'BaseQual');
                Qmat_plan    = xlsread([input_path, input_file_name], 'PlanQual');
                Qmat_max    = xlsread([input_path, input_file_name], 'MaxQual');
                Rmat    = xlsread([input_path, input_file_name], 'Exclusions');
                
                if (sum(size(Qmat_base)==size(Rmat)) + sum(size(Qmat_plan)==size(Rmat)) + sum(size(Qmat_max)==size(Rmat)))<6
                    error('inconsistent matrix found! please check all input matrix')
                end
                Qmat = struct('base', Qmat_base...
                              ,'plan',Qmat_plan...
                              ,'max', Qmat_max...
                              ,'exclusion', Rmat...
                              );
                
                n = size(sht_demand,1); %number of products
                m = size(sht_site,1); %num of sites
                numQuarter = size(sht_demand(:,4:end),2);  %num of quarters
                numOptions = size(Rmat(Rmat==0),1) + size(Rmat(Rmat==2),1); %number of options can be added into qual structure
                
                Pars = struct('num_prod', n...
                             ,'num_site', m...
                             ,'num_quarter', numQuarter...
                             ,'num_option', numOptions...
                             );
                 
                BasicInfo = struct('product', {product} ...
                                   ,'site', {transpose(site)} ...
                                   ,'quarter', {transpose(quarter)}...
                                   );
                  
                D_mu = sht_demand(:,4:end);  %avg demand
                D_bias = D_mu.*sht_demand(:,1); %fcst bias
                %D_bias = D_mu.*repmat(sht_demand(:,1),1,size(D_mu,2));
                D_mu_Adj = D_mu - D_bias;   %unbiased
                D_sig = D_mu.*sht_demand(:,2); %sigma of fcst error
                %D_sig = D_mu.*repmat(sht_demand(:,2),1,size(D_mu,2));
                D_mar = sht_demand(:,3); %demand margin (placeholder)
                
                Demand= struct('fcst', D_mu...
                                ,'bias', D_bias ...
                                ,'rv_mean', D_mu_Adj...
                                ,'rv_std', D_sig...
                                ,'margin', D_mar...
                                );
                Capacity= sht_site(:, 2:end); 
                MinUtil = sht_site(:,1);
end
                
                            
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                

