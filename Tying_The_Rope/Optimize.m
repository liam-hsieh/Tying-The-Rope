function Optimize(obj, varargin)
%%accept at most three args: ref_quarter, keep_raw_ref_quarters,keep_raw_added_links
%%%ref_quarter: int, index of the quearter we wanna optimize the matrix
%%%keep_raw_ref_quarters: logical value, keep raw data of evaluating all matrix in quarter ref_quarter
%%%keep_raw_added_links: logical value, keep raw data of evaluating all new matrix in quarter ref_quarter

isaninteger =@(x)isfinite(x) & x==floor(x);
tol = 1e-8;

%default of args
keep_raw_ref_quarters = obj.Setting.keep_raw.ref_quarters;
keep_raw_added_links = obj.Setting.keep_raw.added_links;

if nargin>4
    error('too many input args!');
elseif nargin==4
    if (islogical(varargin{2}) && islogical(varargin{3}) && isaninteger(varargin{1}) && (varargin{1}<obj.Pars.num_quarter))
        obj.Setting.Ref_quarter = varargin{1};
        keep_raw_ref_quarters = varargin{1};
        keep_raw_added_links =varargin{2};
    else
        error('only allows logical value as keep_raw tag, also check if insert wrong quarter index');
    end
elseif nargin==3
    if (islogical(varargin{2}) && isaninteger(varargin{1}) && (varargin{1}<obj.Pars.num_quarter))
        obj.Setting.Ref_quarter = varargin{1};
        keep_raw_ref_quarters = varargin{2};
        keep_raw_added_links =varargin{2};
    else
        error('only allows logical value as keep_raw tag, also check if insert wrong quarter index');
    end
elseif nargin==2
    if (isaninteger(varargin{1}) && (varargin{1}<obj.Pars.num_quarter))
        obj.Setting.Ref_quarter = varargin{1};
    else
        error('check if insert wrong quarter index');
    end
end

obj.ClearAddedLink();

RS = obj.Evaluate('base', obj.Setting.Ref_quarter, keep_raw_ref_quarters);
obj.RecordNewLink(RS, [], []); % add result of base qual as the first record in Progress

RS = obj.Evaluate('plan', obj.Setting.Ref_quarter, keep_raw_ref_quarters);
obj.RecordNewLink(RS, [], []); 

RS = obj.Evaluate('max', obj.Setting.Ref_quarter, keep_raw_ref_quarters);
obj.RecordNewLink(RS, [], []); 
SL_max = RS{7};

CurrentBestObj = obj.Stat(obj.Setting.Ref_quarter).base.Obj_mean;
CurrentBestSL = obj.Stat(obj.Setting.Ref_quarter).base.SL.mean;
round = 0;

if obj.Setting.SL_Target > 0
    SL_Target = obj.Setting.SL_Target;
elseif obj.Setting.SL_Target==0
    SL_Target = SL_max;
end

while ((CurrentBestSL + tol < SL_Target) && (CurrentBestSL + tol < SL_max*obj.Setting.PctOf_SL_full_Target) && (round<=(min(obj.Pars.num_option, obj.Setting.MaxRound)-1)))
    if round==0
        Ref_Qmat_name='base';
    else
        Ref_Qmat_name=['link' num2str(round)];
    end
    
    [BestLink, Qmat_NextBest] = obj.TheNextBest(Ref_Qmat_name, CurrentBestObj); % format of BestLink is sdesigned to insert a whole row for obj.Progress
    
    added_Qmat_name = ['link' num2str(round+1)];
    
    obj.Qmat.(added_Qmat_name) = Qmat_NextBest; %update the Qmat
    RS = obj.Evaluate(added_Qmat_name, obj.Setting.Ref_quarter, keep_raw_added_links);
    obj.RecordNewLink(BestLink, Ref_Qmat_name, added_qmat_name);
    
    %if ((CurrentBestObj + obj.Setting.tolerance.Obj)>=BestLink{6} &&(CurrentBestSL + obj.Setting.tolerance.SL) >= BestLink{7}),round=10000; end;
    
    CurrentBestObj = BestLink{6};
    CurrentBestSL = BestLink{7};
    round = round + 1;
end

end






        
        
        